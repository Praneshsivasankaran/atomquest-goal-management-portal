from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import os
import re
import sys
import threading
import time
import traceback
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.auth import assert_secret_is_safe, create_token, decode_token
from app.business import DomainError, utc_now
from app.storage import DEFAULT_DB, Store


PUBLIC = ROOT / "public"
try:
    DEMO_TIMEZONE = ZoneInfo("Asia/Kolkata")
except ZoneInfoNotFoundError:
    DEMO_TIMEZONE = timezone(timedelta(hours=5, minutes=30))

LOG = logging.getLogger("atomquest.server")
# Authenticated POST/PATCH/DELETE must come from a known Origin. Defaults match the
# local-dev URLs; production sets APP_ORIGIN to the hosted URL.
ALLOWED_ORIGINS = {
    origin.strip().rstrip("/")
    for origin in os.getenv("APP_ORIGIN", "http://127.0.0.1:8000,http://localhost:8000").split(",")
    if origin.strip()
}

# Token-bucket rate limit per source IP for /api/auth/* endpoints.
AUTH_RATE_LIMIT_WINDOW_SECONDS = 60
AUTH_RATE_LIMIT_MAX_HITS = 5
_auth_attempts: dict[str, deque[float]] = defaultdict(deque)
_auth_attempts_lock = threading.Lock()


def hit_auth_rate_limit(ip: str) -> int:
    """Record an attempt from `ip`. Return seconds-to-retry if rate limit exceeded, else 0."""
    now = time.monotonic()
    cutoff = now - AUTH_RATE_LIMIT_WINDOW_SECONDS
    with _auth_attempts_lock:
        bucket = _auth_attempts[ip]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= AUTH_RATE_LIMIT_MAX_HITS:
            retry_after = max(1, int(AUTH_RATE_LIMIT_WINDOW_SECONDS - (now - bucket[0])))
            return retry_after
        bucket.append(now)
        return 0


def current_demo_date() -> str:
    return datetime.now(DEMO_TIMEZONE).date().isoformat()


def assert_manager_owns_sheet(store: Store, manager_id: int, sheet_id: int) -> dict[str, Any]:
    sheet = store.fetchone("SELECT * FROM goal_sheets WHERE id=?", (sheet_id,))
    if not sheet:
        raise DomainError("Goal sheet not found for this manager", 404)
    employee = store.get_user(sheet["user_id"])
    if employee.get("manager_id") != manager_id:
        raise DomainError("Goal sheet not found for this manager", 404)
    return sheet


def assert_manager_owns_goal(store: Store, manager_id: int, goal_id: int) -> dict[str, Any]:
    goal = store.get_goal(goal_id)
    sheet = store.fetchone("SELECT * FROM goal_sheets WHERE id=?", (goal["sheet_id"],))
    if not sheet:
        raise DomainError("Goal not found for this manager", 404)
    employee = store.get_user(sheet["user_id"])
    if employee.get("manager_id") != manager_id:
        raise DomainError("Goal not found for this manager", 404)
    return goal


class ApiServer(BaseHTTPRequestHandler):
    store: Store

    def log_message(self, fmt: str, *args: Any) -> None:
        if os.getenv("APP_DEBUG"):
            super().log_message(fmt, *args)

    def do_GET(self) -> None:
        self.handle_request("GET")

    def do_POST(self) -> None:
        self.handle_request("POST")

    def do_PATCH(self) -> None:
        self.handle_request("PATCH")

    def do_DELETE(self) -> None:
        self.handle_request("DELETE")

    def handle_request(self, method: str) -> None:
        try:
            parsed = urlparse(self.path)
            path = parsed.path
            if path.startswith("/api/"):
                if method in ("POST", "PATCH", "DELETE"):
                    self._assert_origin_allowed()
                self.route_api(method, path, parse_qs(parsed.query))
            else:
                self.serve_static(path)
        except DomainError as exc:
            self.send_json({"error": exc.message}, exc.status)
        except Exception:
            # Log full traceback server-side; never leak it to the client.
            LOG.error("Unhandled error on %s %s\n%s", method, self.path, traceback.format_exc())
            self.send_json({"error": "Something went wrong"}, 500)

    def _assert_origin_allowed(self) -> None:
        """Reject state-changing API calls from unexpected origins.

        Why: tokens travel in the Authorization header, so a logged-in user visiting
        a malicious page would otherwise have their browser attach the token to
        cross-origin POSTs. Comparing Origin (or Referer fallback) blocks that.
        """
        origin = (self.headers.get("Origin") or "").rstrip("/")
        if not origin:
            referer = (self.headers.get("Referer") or "").rstrip("/")
            if not referer:
                return  # same-origin tools (curl, mobile) don't send Origin/Referer
            parsed = urlparse(referer)
            origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in ALLOWED_ORIGINS:
            raise DomainError("Origin not allowed", 403)

    def _client_ip(self) -> str:
        forwarded = self.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return self.client_address[0] if self.client_address else "unknown"

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, body: str, content_type: str, status: int = 200) -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def current_user(self) -> dict[str, Any]:
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise DomainError("Authentication required", 401)
        payload = decode_token(auth.replace("Bearer ", "", 1))
        return self.store.get_user(int(payload["sub"]))

    def require_role(self, *roles: str) -> dict[str, Any]:
        user = self.current_user()
        if user["role"] not in roles:
            raise DomainError("You do not have access to this action", 403)
        return user

    def route_api(self, method: str, path: str, query: dict[str, list[str]]) -> None:
        if method == "POST" and path == "/api/auth/login":
            retry_after = hit_auth_rate_limit(self._client_ip())
            if retry_after:
                self.send_response(429)
                self.send_header("Retry-After", str(retry_after))
                self.send_header("Content-Type", "application/json; charset=utf-8")
                body = json.dumps({"error": f"Too many sign-in attempts. Try again in {retry_after}s."}).encode("utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            payload = self.read_json()
            user = self.store.authenticate(payload.get("email", ""), payload.get("password", ""))
            return self.send_json({"token": create_token(user), "user": user})

        if method == "POST" and path == "/api/auth/signup":
            retry_after = hit_auth_rate_limit(self._client_ip())
            if retry_after:
                self.send_response(429)
                self.send_header("Retry-After", str(retry_after))
                self.send_header("Content-Type", "application/json; charset=utf-8")
                body = json.dumps({"error": f"Too many signup attempts. Try again in {retry_after}s."}).encode("utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            user = self.store.register_user(self.read_json())
            return self.send_json({"token": create_token(user), "user": user}, 201)

        if method == "GET" and path == "/api/me":
            user = self.current_user()
            return self.send_json({"user": user})

        if method == "GET" and path == "/api/app-state":
            user = self.current_user()
            return self.send_json(self.store.app_state(user))

        if method == "GET" and path == "/api/reports/achievement.csv":
            self.require_role("manager", "admin")
            csv_body = self.store.achievement_csv()
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", "attachment; filename=achievement-report.csv")
            self.send_header("Content-Length", str(len(csv_body.encode("utf-8"))))
            self.end_headers()
            return self.wfile.write(csv_body.encode("utf-8"))

        if method == "GET" and path == "/api/reports/achievement.xlsx":
            self.require_role("manager", "admin")
            body = self.store.achievement_xlsx()
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            self.send_header("Content-Disposition", "attachment; filename=achievement-report.xlsx")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return self.wfile.write(body)

        if method == "GET" and path == "/api/goals/suggestions":
            user = self.require_role("employee")
            return self.send_json({"suggestions": self.store.goal_suggestions(user["id"])})

        if method == "POST" and path == "/api/goals":
            user = self.require_role("employee")
            goal = self.store.create_goal(user["id"], user["id"], self.read_json())
            return self.send_json(goal, 201)

        match = re.fullmatch(r"/api/goals/(\d+)", path)
        if match and method == "PATCH":
            user = self.require_role("employee")
            goal = self.store.get_goal(int(match.group(1)))
            sheet = self.store.fetchone("SELECT * FROM goal_sheets WHERE id=?", (goal["sheet_id"],))
            if sheet["user_id"] != user["id"]:
                raise DomainError("Employees can only edit their own goals", 403)
            return self.send_json(self.store.update_goal(user["id"], int(match.group(1)), self.read_json()))

        if match and method == "DELETE":
            user = self.require_role("employee")
            goal = self.store.get_goal(int(match.group(1)))
            sheet = self.store.fetchone("SELECT * FROM goal_sheets WHERE id=?", (goal["sheet_id"],))
            if sheet["user_id"] != user["id"]:
                raise DomainError("Employees can only delete their own goals", 403)
            self.store.delete_goal(user["id"], int(match.group(1)))
            return self.send_json({"ok": True})

        if method == "POST" and path == "/api/goal-sheet/submit":
            user = self.require_role("employee")
            return self.send_json(self.store.submit_sheet(user["id"]))

        match = re.fullmatch(r"/api/goals/(\d+)/progress", path)
        if match and method == "POST":
            user = self.require_role("employee")
            return self.send_json(self.store.add_progress(user["id"], int(match.group(1)), self.read_json()))

        match = re.fullmatch(r"/api/manager/goals/(\d+)", path)
        if match and method == "PATCH":
            user = self.require_role("manager")
            goal_id = int(match.group(1))
            assert_manager_owns_goal(self.store, user["id"], goal_id)
            return self.send_json(self.store.update_goal(user["id"], goal_id, self.read_json(), manager_edit=True))

        match = re.fullmatch(r"/api/manager/sheets/(\d+)/approve", path)
        if match and method == "POST":
            user = self.require_role("manager")
            sheet_id = int(match.group(1))
            assert_manager_owns_sheet(self.store, user["id"], sheet_id)
            return self.send_json(self.store.approve_sheet(user["id"], sheet_id))

        match = re.fullmatch(r"/api/manager/sheets/(\d+)/return", path)
        if match and method == "POST":
            user = self.require_role("manager")
            sheet_id = int(match.group(1))
            assert_manager_owns_sheet(self.store, user["id"], sheet_id)
            return self.send_json(self.store.return_sheet(user["id"], sheet_id, self.read_json().get("comment", "")))

        match = re.fullmatch(r"/api/manager/sheets/(\d+)/checkins", path)
        if match and method == "POST":
            user = self.require_role("manager")
            sheet_id = int(match.group(1))
            assert_manager_owns_sheet(self.store, user["id"], sheet_id)
            return self.send_json(self.store.add_checkin(user["id"], sheet_id, self.read_json()))

        if method == "POST" and path == "/api/admin/shared-goals":
            user = self.require_role("admin")
            return self.send_json(self.store.create_shared_goal(user["id"], self.read_json()), 201)

        if method == "POST" and path == "/api/admin/demo-mode":
            user = self.require_role("admin")
            today = self.read_json().get("today") or current_demo_date()
            windows = self.store.activate_demo_windows(user["id"], today)
            return self.send_json({"windows": windows})

        match = re.fullmatch(r"/api/admin/users/(\d+)", path)
        if match and method == "PATCH":
            user = self.require_role("admin")
            updated = self.store.update_user(user["id"], int(match.group(1)), self.read_json())
            return self.send_json(updated)

        match = re.fullmatch(r"/api/admin/sheets/(\d+)/unlock", path)
        if match and method == "POST":
            user = self.require_role("admin")
            return self.send_json(self.store.unlock_sheet(user["id"], int(match.group(1)), self.read_json().get("reason", "")))

        match = re.fullmatch(r"/api/admin/windows/([a-z0-9_]+)", path)
        if match and method == "PATCH":
            user = self.require_role("admin")
            payload = self.read_json()
            phase = match.group(1)
            cycle = self.store.active_cycle()
            before = self.store.fetchone("SELECT * FROM cycle_windows WHERE cycle_id=? AND phase=?", (cycle["id"], phase))
            if not before:
                raise DomainError("Cycle window not found", 404)
            opens = payload.get("opens_on") or before["opens_on"]
            closes = payload.get("closes_on") or before["closes_on"]
            self.store.execute(
                "UPDATE cycle_windows SET opens_on=?, closes_on=? WHERE id=?",
                (opens, closes, before["id"]),
            )
            after = self.store.fetchone("SELECT * FROM cycle_windows WHERE id=?", (before["id"],))
            self.store.audit(user["id"], "cycle_window", before["id"], "updated", before, after, "Admin adjusted active cycle window")
            return self.send_json(after)

        raise DomainError("Route not found", 404)

    def serve_static(self, path: str) -> None:
        if path in {"", "/"}:
            path = "/index.html"
        target = (PUBLIC / path.lstrip("/")).resolve()
        if not str(target).startswith(str(PUBLIC.resolve())) or not target.exists() or not target.is_file():
            target = PUBLIC / "index.html"
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_server(port: int, db_path: str | Path = DEFAULT_DB, host: str = "127.0.0.1") -> None:
    assert_secret_is_safe(host)
    logging.basicConfig(level=os.getenv("APP_LOG_LEVEL", "INFO"))
    ApiServer.store = Store(db_path)
    httpd = ThreadingHTTPServer((host, port), ApiServer)
    print(f"Goal portal running at http://{host}:{port}")
    httpd.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AtomQuest Goal Portal demo server.")
    parser.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--seed-only", action="store_true")
    args = parser.parse_args()

    if args.seed_only:
        store = Store(args.db)
        store.reset_demo_data()
        store.close()
        print(f"Demo data reset at {utc_now()}")
        return

    run_server(args.port, args.db, args.host)


if __name__ == "__main__":
    main()
