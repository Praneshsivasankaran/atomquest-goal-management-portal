from __future__ import annotations

from datetime import date, datetime
from typing import Any


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


def utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


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
    if len(goals) > 8:
        raise DomainError("An employee can have a maximum of 8 goals")

    total = 0.0
    for goal in goals:
        weightage = to_number(goal.get("weightage"), "Weightage")
        if weightage < 10:
            raise DomainError("Each goal must have at least 10% weightage")
        total += weightage

    if round(total, 2) != 100:
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


def ensure_window_open(window: dict[str, Any] | None, today: date | None = None) -> None:
    if not window:
        raise DomainError("No active window is configured for this action", 409)

    today = today or date.today()
    opens = parse_date(window.get("opens_on"))
    closes = parse_date(window.get("closes_on"))
    if opens and today < opens:
        raise DomainError(f"This window opens on {opens.isoformat()}", 409)
    if closes and today > closes:
        raise DomainError(f"This window closed on {closes.isoformat()}", 409)

