from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.auth import create_token, decode_token
from app.business import DomainError, utc_now
from app.storage import DEFAULT_DB, Store


PUBLIC = ROOT / "public"


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
                self.route_api(method, path, parse_qs(parsed.query))
            else:
                self.serve_static(path)
        except DomainError as exc:
            self.send_json({"error": exc.message}, exc.status)
        except Exception as exc:
            self.send_json({"error": "Something went wrong", "detail": str(exc)}, 500)

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
            payload = self.read_json()
            user = self.store.authenticate(payload.get("email", ""), payload.get("password", ""))
            return self.send_json({"token": create_token(user), "user": user})

        if method == "POST" and path == "/api/auth/signup":
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
            return self.send_json(self.store.update_goal(user["id"], int(match.group(1)), self.read_json(), manager_edit=True))

        match = re.fullmatch(r"/api/manager/sheets/(\d+)/approve", path)
        if match and method == "POST":
            user = self.require_role("manager")
            return self.send_json(self.store.approve_sheet(user["id"], int(match.group(1))))

        match = re.fullmatch(r"/api/manager/sheets/(\d+)/return", path)
        if match and method == "POST":
            user = self.require_role("manager")
            return self.send_json(self.store.return_sheet(user["id"], int(match.group(1)), self.read_json().get("comment", "")))

        match = re.fullmatch(r"/api/manager/sheets/(\d+)/checkins", path)
        if match and method == "POST":
            user = self.require_role("manager")
            return self.send_json(self.store.add_checkin(user["id"], int(match.group(1)), self.read_json()))

        if method == "POST" and path == "/api/admin/shared-goals":
            user = self.require_role("admin")
            return self.send_json(self.store.create_shared_goal(user["id"], self.read_json()), 201)

        if method == "POST" and path == "/api/admin/demo-mode":
            user = self.require_role("admin")
            windows = self.store.activate_demo_windows(user["id"], self.read_json().get("today", "2026-05-18"))
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
