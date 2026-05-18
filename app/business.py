from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python < 3.9 fallback (shouldn't happen on target runtime)
    ZoneInfo = None  # type: ignore


class DomainError(ValueError):
    """Raised when a workflow rule is violated."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


GOAL_STATES = {"draft", "submitted", "returned", "approved", "locked", "unlocked"}
UOM_TYPES = {"numeric", "percentage", "timeline", "zero"}
DIRECTIONS = {"min", "max", "timeline", "zero"}
QUARTERS = {"q1", "q2", "q3", "q4"}
PROGRESS_STATUSES = {"not_started", "on_track", "completed"}
EDITABLE_STATES = {"draft", "returned", "unlocked"}
MAX_GOALS_PER_EMPLOYEE = 8
MAX_GOALS_ERROR = f"An employee can have a maximum of {MAX_GOALS_PER_EMPLOYEE} goals"
DEFAULT_CYCLE_TZ = "Asia/Kolkata"


def utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def cycle_today(tz_name: str | None = None) -> date:
    """Return today's date in the cycle's configured timezone.

    Cycle windows are stamped with a timezone (default Asia/Kolkata). Using
    ``date.today()`` directly would pick up the server's local date instead,
    which can be off by several hours on a UTC host around boundaries.
    """
    name = tz_name or DEFAULT_CYCLE_TZ
    if ZoneInfo is None:
        return datetime.utcnow().date()
    try:
        return datetime.now(ZoneInfo(name)).date()
    except Exception:
        return datetime.now(timezone.utc).date()


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value[:10])


def to_number(value: Any, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise DomainError(f"{field} must be a number") from exc


def validate_goal_payload(payload: dict[str, Any], partial: bool = False) -> None:
    required = ["thrust_area", "title", "uom_type", "direction", "weightage"]
    if not partial:
        for field in required:
            if payload.get(field) in (None, ""):
                raise DomainError(f"{field.replace('_', ' ').title()} is required")

    uom_type = payload.get("uom_type")
    if uom_type is not None and uom_type not in UOM_TYPES:
        raise DomainError("Unsupported unit of measurement")

    direction = payload.get("direction")
    if direction is not None and direction not in DIRECTIONS:
        raise DomainError("Unsupported scoring direction")

    if "weightage" in payload:
        weightage = to_number(payload.get("weightage"), "Weightage")
        if weightage < 10:
            raise DomainError("Each goal must have at least 10% weightage")

    effective_uom = uom_type or payload.get("current_uom_type")
    if effective_uom == "timeline":
        if not partial and not payload.get("target_date"):
            raise DomainError("Timeline goals require a deadline")
        if payload.get("target_date"):
            parse_date(payload["target_date"])
    elif effective_uom in {"numeric", "percentage", "zero"}:
        if not partial and payload.get("target_value") in (None, ""):
            raise DomainError("Numeric, percentage, and zero-based goals require a target")
        if payload.get("target_value") not in (None, ""):
            to_number(payload.get("target_value"), "Target")


def validate_goal_sheet(goals: list[dict[str, Any]]) -> None:
    if not goals:
        raise DomainError("Add at least one goal before submitting")
    if len(goals) >= MAX_GOALS_PER_EMPLOYEE:
        raise DomainError(MAX_GOALS_ERROR)

    try:
        total = sum(Decimal(str(g.get("weightage", 0))) for g in goals)
    except InvalidOperation as exc:
        raise DomainError("Weightage must be a number") from exc

    for goal in goals:
        weightage = Decimal(str(goal.get("weightage", 0)))
        if weightage < Decimal("10"):
            raise DomainError("Each goal must have at least 10% weightage")

    if total != Decimal("100"):
        raise DomainError(f"Total goal weightage must be exactly 100%. Current total is {total:g}%.")


def ensure_sheet_editable(state: str) -> None:
    if state not in EDITABLE_STATES:
        raise DomainError("This goal sheet is locked. Ask Admin/HR to unlock it.")


def normalize_score(value: float) -> float:
    if value < 0:
        return 0.0
    return round(min(value, 1.0) * 100, 2)


def calculate_progress(goal: dict[str, Any], actual_value: Any = None, completion_date: str | None = None) -> float:
    uom_type = goal.get("uom_type")
    direction = goal.get("direction")

    if uom_type == "timeline" or direction == "timeline":
        deadline = parse_date(goal.get("target_date"))
        finished = parse_date(completion_date)
        if not deadline or not finished:
            return 0.0
        return 100.0 if finished <= deadline else 0.0

    if uom_type == "zero" or direction == "zero":
        actual = to_number(actual_value, "Actual achievement")
        return 100.0 if actual == 0 else 0.0

    target = to_number(goal.get("target_value"), "Target")
    actual = to_number(actual_value, "Actual achievement")

    if target == 0 and actual == 0:
        return 100.0
    if target == 0:
        return 0.0

    if direction == "max":
        if actual == 0:
            return 100.0
        return normalize_score(target / actual)

    return normalize_score(actual / target)


def validate_progress_payload(goal: dict[str, Any], payload: dict[str, Any]) -> None:
    quarter = payload.get("quarter")
    if quarter not in QUARTERS:
        raise DomainError("Select a valid quarter")

    status = payload.get("status")
    if status not in PROGRESS_STATUSES:
        raise DomainError("Select a valid progress status")

    if goal.get("uom_type") == "timeline":
        if not payload.get("completion_date"):
            raise DomainError("Timeline progress requires a completion date")
        parse_date(payload["completion_date"])
    else:
        to_number(payload.get("actual_value"), "Actual achievement")


def ensure_window_open(window: dict[str, Any] | None, today: date | None = None, tz_name: str | None = None) -> None:
    if not window:
        raise DomainError("No active window is configured for this action", 409)

    today = today or cycle_today(tz_name)
    opens = parse_date(window.get("opens_on"))
    closes = parse_date(window.get("closes_on"))
    if opens and today < opens:
        raise DomainError(f"This window opens on {opens.isoformat()}", 409)
    if closes and today > closes:
        raise DomainError(f"This window closed on {closes.isoformat()}", 409)
