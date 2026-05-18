from __future__ import annotations

import csv
import hashlib
import io
import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from app.business import (
    DomainError,
    calculate_progress,
    ensure_sheet_editable,
    ensure_window_open,
    utc_now,
    validate_goal_payload,
    validate_goal_sheet,
    validate_progress_payload,
)


DEFAULT_DB = Path(__file__).resolve().parent.parent / "goal_portal.sqlite3"


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class Store:
    def __init__(self, db_path: str | Path = DEFAULT_DB):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_schema()
        self.seed_if_empty()

    def close(self) -> None:
        with self.lock:
            self.conn.close()

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        with self.lock:
            cur = self.conn.execute(sql, params)
            self.conn.commit()
            return cur

    def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        with self.lock:
            return row_to_dict(self.conn.execute(sql, params).fetchone())

    def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self.lock:
            return [dict(row) for row in self.conn.execute(sql, params).fetchall()]

    def create_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              email TEXT UNIQUE NOT NULL,
              password_hash TEXT NOT NULL,
              role TEXT NOT NULL,
              title TEXT,
              department TEXT,
              manager_id INTEGER REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS cycles (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              year INTEGER NOT NULL,
              status TEXT NOT NULL DEFAULT 'active',
              timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata'
            );

            CREATE TABLE IF NOT EXISTS cycle_windows (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              cycle_id INTEGER NOT NULL REFERENCES cycles(id),
              phase TEXT NOT NULL,
              label TEXT NOT NULL,
              opens_on TEXT NOT NULL,
              closes_on TEXT NOT NULL,
              UNIQUE(cycle_id, phase)
            );

            CREATE TABLE IF NOT EXISTS goal_sheets (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL REFERENCES users(id),
              cycle_id INTEGER NOT NULL REFERENCES cycles(id),
              state TEXT NOT NULL DEFAULT 'draft',
              manager_comment TEXT,
              submitted_at TEXT,
              approved_at TEXT,
              locked_at TEXT,
              unlocked_at TEXT,
              unlock_reason TEXT,
              UNIQUE(user_id, cycle_id)
            );

            CREATE TABLE IF NOT EXISTS shared_goals (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              thrust_area TEXT NOT NULL,
              title TEXT NOT NULL,
              description TEXT,
              uom_type TEXT NOT NULL,
              direction TEXT NOT NULL,
              target_value REAL,
              target_date TEXT,
              primary_owner_id INTEGER NOT NULL REFERENCES users(id),
              created_by INTEGER NOT NULL REFERENCES users(id),
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS goals (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              sheet_id INTEGER NOT NULL REFERENCES goal_sheets(id),
              shared_goal_id INTEGER REFERENCES shared_goals(id),
              thrust_area TEXT NOT NULL,
              title TEXT NOT NULL,
              description TEXT,
              uom_type TEXT NOT NULL,
              direction TEXT NOT NULL,
              target_value REAL,
              target_date TEXT,
              weightage REAL NOT NULL,
              locked INTEGER NOT NULL DEFAULT 0,
              created_by INTEGER NOT NULL REFERENCES users(id),
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS progress_updates (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              goal_id INTEGER NOT NULL REFERENCES goals(id),
              shared_goal_id INTEGER REFERENCES shared_goals(id),
              quarter TEXT NOT NULL,
              actual_value REAL,
              completion_date TEXT,
              status TEXT NOT NULL,
              score REAL NOT NULL,
              notes TEXT,
              created_by INTEGER NOT NULL REFERENCES users(id),
              updated_at TEXT NOT NULL,
              UNIQUE(goal_id, quarter)
            );

            CREATE TABLE IF NOT EXISTS checkins (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              sheet_id INTEGER NOT NULL REFERENCES goal_sheets(id),
              manager_id INTEGER NOT NULL REFERENCES users(id),
              quarter TEXT NOT NULL,
              comment TEXT NOT NULL,
              created_at TEXT NOT NULL,
              UNIQUE(sheet_id, quarter)
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              actor_id INTEGER NOT NULL REFERENCES users(id),
              entity_type TEXT NOT NULL,
              entity_id INTEGER NOT NULL,
              action TEXT NOT NULL,
              before_json TEXT,
              after_json TEXT,
              reason TEXT,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS escalation_rules (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              condition_key TEXT NOT NULL,
              days_after INTEGER NOT NULL,
              notify_role TEXT NOT NULL,
              enabled INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS escalation_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              rule_id INTEGER NOT NULL REFERENCES escalation_rules(id),
              user_id INTEGER REFERENCES users(id),
              sheet_id INTEGER REFERENCES goal_sheets(id),
              status TEXT NOT NULL,
              message TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def reset_demo_data(self) -> None:
        self.conn.executescript(
            """
            DELETE FROM escalation_events;
            DELETE FROM escalation_rules;
            DELETE FROM audit_logs;
            DELETE FROM checkins;
            DELETE FROM progress_updates;
            DELETE FROM goals;
            DELETE FROM shared_goals;
            DELETE FROM goal_sheets;
            DELETE FROM cycle_windows;
            DELETE FROM cycles;
            DELETE FROM users;
            DELETE FROM sqlite_sequence WHERE name IN (
              'users','cycles','cycle_windows','goal_sheets','shared_goals','goals',
              'progress_updates','checkins','audit_logs','escalation_rules','escalation_events'
            );
            """
        )
        self.conn.commit()
        self.seed_demo_data()

    def seed_if_empty(self) -> None:
        existing = self.fetchone("SELECT id FROM users LIMIT 1")
        if not existing:
            self.seed_demo_data()

    def seed_demo_data(self) -> None:
        password = hash_password("demo123")
        users = [
            (2, "Mohan Kumar", "manager@demo.com", password, "manager", "L1 Manager", "Sales", None),
            (3, "Riya Shah", "admin@demo.com", password, "admin", "HR Business Partner", "People Ops", None),
            (1, "Anita Rao", "employee@demo.com", password, "employee", "Sales Executive", "Sales", 2),
            (4, "Dev Menon", "employee2@demo.com", password, "employee", "Customer Success Associate", "Customer Success", 2),
            (5, "Sara Iyer", "employee3@demo.com", password, "employee", "Operations Analyst", "Operations", 2),
        ]
        for user_id, name, email, pwd, role, title, department, manager_id in users:
            self.execute(
                "INSERT INTO users (id,name,email,password_hash,role,title,department,manager_id) VALUES (?,?,?,?,?,?,?,?)",
                (user_id, name, email, pwd, role, title, department, manager_id),
            )

        self.execute("INSERT INTO cycles (name, year, status, timezone) VALUES (?,?,?,?)", ("FY 2026 Goal Cycle", 2026, "active", "Asia/Kolkata"))
        cycle_id = self.fetchone("SELECT id FROM cycles WHERE status='active'")["id"]
        windows = [
            ("goal_setting", "Phase 1 - Goal Setting", "2026-05-01", "2026-05-31"),
            ("q1", "Q1 Check-in", "2026-07-01", "2026-07-31"),
            ("q2", "Q2 Check-in", "2026-10-01", "2026-10-31"),
            ("q3", "Q3 Check-in", "2027-01-01", "2027-01-31"),
            ("q4", "Q4 / Annual Review", "2027-03-01", "2027-04-30"),
        ]
        for phase, label, opens, closes in windows:
            self.execute(
                "INSERT INTO cycle_windows (cycle_id, phase, label, opens_on, closes_on) VALUES (?,?,?,?,?)",
                (cycle_id, phase, label, opens, closes),
            )

        for user_id in [1, 4, 5]:
            self.execute("INSERT INTO goal_sheets (user_id, cycle_id, state) VALUES (?,?,?)", (user_id, cycle_id, "draft"))

        self.create_goal(1, 1, {
            "thrust_area": "Revenue Growth",
            "title": "Increase enterprise sales revenue",
            "description": "Close high-value enterprise opportunities in the western region.",
            "uom_type": "numeric",
            "direction": "min",
            "target_value": 1000000,
            "weightage": 40,
        }, audit=False)
        self.create_goal(1, 1, {
            "thrust_area": "Customer Quality",
            "title": "Maintain customer satisfaction",
            "description": "Keep post-demo satisfaction high across strategic accounts.",
            "uom_type": "percentage",
            "direction": "min",
            "target_value": 95,
            "weightage": 30,
        }, audit=False)
        self.create_goal(1, 1, {
            "thrust_area": "Delivery",
            "title": "Submit quarterly account plan on time",
            "description": "Publish the account plan before the Q1 deadline.",
            "uom_type": "timeline",
            "direction": "timeline",
            "target_date": "2026-06-01",
            "weightage": 30,
        }, audit=False)

        sheet_dev = self.get_sheet_for_user(4)
        self.create_goal(2, 4, {
            "thrust_area": "Customer Experience",
            "title": "Reduce support ticket backlog",
            "description": "Bring open support backlog under the agreed threshold.",
            "uom_type": "numeric",
            "direction": "max",
            "target_value": 15,
            "weightage": 50,
        }, audit=False)
        self.create_goal(2, 4, {
            "thrust_area": "Process",
            "title": "Close renewal health reviews",
            "description": "Complete renewal health checks for assigned accounts.",
            "uom_type": "percentage",
            "direction": "min",
            "target_value": 100,
            "weightage": 50,
        }, audit=False)
        self.execute(
            "UPDATE goal_sheets SET state='submitted', submitted_at=? WHERE id=?",
            (utc_now(), sheet_dev["id"]),
        )

        self.execute(
            "INSERT INTO escalation_rules (name, condition_key, days_after, notify_role) VALUES (?,?,?,?)",
            ("Goal sheet not submitted", "employee_goal_submission_missing", 3, "manager"),
        )
        self.execute(
            "INSERT INTO escalation_rules (name, condition_key, days_after, notify_role) VALUES (?,?,?,?)",
            ("Manager approval pending", "manager_approval_pending", 2, "admin"),
        )
        self.execute(
            """
            INSERT INTO escalation_events (rule_id, user_id, sheet_id, status, message, created_at)
            VALUES (?,?,?,?,?,?)
            """,
            (1, 5, 3, "open", "Sara Iyer has not submitted her goal sheet for the active cycle.", utc_now()),
        )
        self.execute(
            """
            INSERT INTO escalation_events (rule_id, user_id, sheet_id, status, message, created_at)
            VALUES (?,?,?,?,?,?)
            """,
            (2, 4, 2, "open", "Dev Menon's submitted goal sheet is waiting for manager approval.", utc_now()),
        )

    def user_public(self, user: dict[str, Any]) -> dict[str, Any]:
        return {key: user[key] for key in ["id", "name", "email", "role", "title", "department", "manager_id"] if key in user}

    def authenticate(self, email: str, password: str) -> dict[str, Any]:
        user = self.fetchone("SELECT * FROM users WHERE lower(email)=lower(?)", (email,))
        if not user or user["password_hash"] != hash_password(password):
            raise DomainError("Invalid email or password", 401)
        return self.user_public(user)

    def get_user(self, user_id: int) -> dict[str, Any]:
        user = self.fetchone("SELECT * FROM users WHERE id=?", (user_id,))
        if not user:
            raise DomainError("User not found", 404)
        return self.user_public(user)

    def active_cycle(self) -> dict[str, Any]:
        cycle = self.fetchone("SELECT * FROM cycles WHERE status='active' ORDER BY id DESC LIMIT 1")
        if not cycle:
            raise DomainError("No active cycle configured", 409)
        cycle["windows"] = self.fetchall("SELECT * FROM cycle_windows WHERE cycle_id=? ORDER BY id", (cycle["id"],))
        return cycle

    def goal_window(self) -> dict[str, Any] | None:
        cycle = self.active_cycle()
        return self.fetchone("SELECT * FROM cycle_windows WHERE cycle_id=? AND phase='goal_setting'", (cycle["id"],))

    def quarter_window(self, quarter: str) -> dict[str, Any] | None:
        cycle = self.active_cycle()
        return self.fetchone("SELECT * FROM cycle_windows WHERE cycle_id=? AND phase=?", (cycle["id"], quarter))

    def get_sheet_for_user(self, user_id: int) -> dict[str, Any]:
        cycle = self.active_cycle()
        sheet = self.fetchone("SELECT * FROM goal_sheets WHERE user_id=? AND cycle_id=?", (user_id, cycle["id"]))
        if not sheet:
            cur = self.execute("INSERT INTO goal_sheets (user_id, cycle_id, state) VALUES (?,?,?)", (user_id, cycle["id"], "draft"))
            sheet = self.fetchone("SELECT * FROM goal_sheets WHERE id=?", (cur.lastrowid,))
        return sheet

    def get_goal(self, goal_id: int) -> dict[str, Any]:
        goal = self.fetchone("SELECT * FROM goals WHERE id=?", (goal_id,))
        if not goal:
            raise DomainError("Goal not found", 404)
        return goal

    def sheet_goals(self, sheet_id: int) -> list[dict[str, Any]]:
        goals = self.fetchall("SELECT * FROM goals WHERE sheet_id=? ORDER BY id", (sheet_id,))
        for goal in goals:
            goal["progress"] = self.fetchall("SELECT * FROM progress_updates WHERE goal_id=? ORDER BY quarter", (goal["id"],))
        return goals

    def hydrate_sheet(self, sheet_id: int) -> dict[str, Any]:
        sheet = self.fetchone(
            """
            SELECT gs.*, u.name AS employee_name, u.email AS employee_email, u.department, u.manager_id
            FROM goal_sheets gs
            JOIN users u ON u.id = gs.user_id
            WHERE gs.id=?
            """,
            (sheet_id,),
        )
        if not sheet:
            raise DomainError("Goal sheet not found", 404)
        sheet["goals"] = self.sheet_goals(sheet_id)
        sheet["checkins"] = self.fetchall("SELECT * FROM checkins WHERE sheet_id=? ORDER BY quarter", (sheet_id,))
        return sheet

    def audit(self, actor_id: int, entity_type: str, entity_id: int, action: str, before: Any = None, after: Any = None, reason: str | None = None) -> None:
        self.execute(
            """
            INSERT INTO audit_logs (actor_id, entity_type, entity_id, action, before_json, after_json, reason, created_at)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                actor_id,
                entity_type,
                entity_id,
                action,
                json.dumps(before, default=str) if before is not None else None,
                json.dumps(after, default=str) if after is not None else None,
                reason,
                utc_now(),
            ),
        )

    def create_goal(self, actor_id: int, employee_id: int, payload: dict[str, Any], audit: bool = True) -> dict[str, Any]:
        sheet = self.get_sheet_for_user(employee_id)
        ensure_sheet_editable(sheet["state"])
        goals = self.sheet_goals(sheet["id"])
        if len(goals) >= 8:
            raise DomainError("An employee can have a maximum of 8 goals")

        validate_goal_payload(payload)
        cur = self.execute(
            """
            INSERT INTO goals (
              sheet_id, shared_goal_id, thrust_area, title, description, uom_type, direction,
              target_value, target_date, weightage, locked, created_by, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                sheet["id"],
                payload.get("shared_goal_id"),
                payload["thrust_area"],
                payload["title"],
                payload.get("description", ""),
                payload["uom_type"],
                payload["direction"],
                payload.get("target_value"),
                payload.get("target_date"),
                float(payload["weightage"]),
                0,
                actor_id,
                utc_now(),
            ),
        )
        goal = self.get_goal(cur.lastrowid)
        if audit:
            self.audit(actor_id, "goal", goal["id"], "created", None, goal)
        return goal

    def update_goal(self, actor_id: int, goal_id: int, payload: dict[str, Any], manager_edit: bool = False) -> dict[str, Any]:
        before = self.get_goal(goal_id)
        sheet = self.fetchone("SELECT * FROM goal_sheets WHERE id=?", (before["sheet_id"],))
        if not sheet:
            raise DomainError("Goal sheet not found", 404)

        if before.get("shared_goal_id") and not manager_edit:
            allowed = {"weightage"}
            if any(key not in allowed for key in payload):
                raise DomainError("Shared goal recipients can only edit weightage")

        if manager_edit:
            if sheet["state"] != "submitted":
                raise DomainError("Managers can only edit submitted goals during review")
            allowed = {"target_value", "target_date", "weightage", "description"}
        else:
            ensure_sheet_editable(sheet["state"])
            allowed = {"thrust_area", "title", "description", "uom_type", "direction", "target_value", "target_date", "weightage"}

        patch = {key: payload[key] for key in payload if key in allowed}
        if not patch:
            raise DomainError("No supported fields were provided")

        validate_goal_payload({**before, **patch, "current_uom_type": before["uom_type"]}, partial=True)

        assignments = ", ".join([f"{key}=?" for key in patch] + ["updated_at=?"])
        params = [patch[key] for key in patch] + [utc_now(), goal_id]
        self.execute(f"UPDATE goals SET {assignments} WHERE id=?", tuple(params))
        after = self.get_goal(goal_id)
        self.audit(actor_id, "goal", goal_id, "updated", before, after)
        return after

    def delete_goal(self, actor_id: int, goal_id: int) -> None:
        before = self.get_goal(goal_id)
        sheet = self.fetchone("SELECT * FROM goal_sheets WHERE id=?", (before["sheet_id"],))
        ensure_sheet_editable(sheet["state"])
        self.execute("DELETE FROM goals WHERE id=?", (goal_id,))
        self.audit(actor_id, "goal", goal_id, "deleted", before, None)

    def submit_sheet(self, actor_id: int) -> dict[str, Any]:
        window = self.goal_window()
        ensure_window_open(window)
        sheet = self.get_sheet_for_user(actor_id)
        ensure_sheet_editable(sheet["state"])
        goals = self.sheet_goals(sheet["id"])
        validate_goal_sheet(goals)
        before = dict(sheet)
        self.execute("UPDATE goal_sheets SET state='submitted', submitted_at=?, manager_comment=NULL WHERE id=?", (utc_now(), sheet["id"]))
        after = self.hydrate_sheet(sheet["id"])
        self.audit(actor_id, "goal_sheet", sheet["id"], "submitted", before, after)
        return after

    def approve_sheet(self, manager_id: int, sheet_id: int) -> dict[str, Any]:
        sheet = self.fetchone(
            """
            SELECT gs.* FROM goal_sheets gs
            JOIN users u ON u.id = gs.user_id
            WHERE gs.id=? AND u.manager_id=?
            """,
            (sheet_id, manager_id),
        )
        if not sheet:
            raise DomainError("Goal sheet not found for this manager", 404)
        if sheet["state"] != "submitted":
            raise DomainError("Only submitted goal sheets can be approved")
        goals = self.sheet_goals(sheet_id)
        validate_goal_sheet(goals)
        before = self.hydrate_sheet(sheet_id)
        now = utc_now()
        self.execute("UPDATE goal_sheets SET state='locked', approved_at=?, locked_at=?, manager_comment=NULL WHERE id=?", (now, now, sheet_id))
        self.execute("UPDATE goals SET locked=1 WHERE sheet_id=?", (sheet_id,))
        after = self.hydrate_sheet(sheet_id)
        self.audit(manager_id, "goal_sheet", sheet_id, "approved_and_locked", before, after)
        return after

    def return_sheet(self, manager_id: int, sheet_id: int, comment: str) -> dict[str, Any]:
        if not comment.strip():
            raise DomainError("Return comment is required")
        sheet = self.fetchone(
            """
            SELECT gs.* FROM goal_sheets gs
            JOIN users u ON u.id = gs.user_id
            WHERE gs.id=? AND u.manager_id=?
            """,
            (sheet_id, manager_id),
        )
        if not sheet:
            raise DomainError("Goal sheet not found for this manager", 404)
        if sheet["state"] != "submitted":
            raise DomainError("Only submitted goal sheets can be returned")
        before = dict(sheet)
        self.execute("UPDATE goal_sheets SET state='returned', manager_comment=? WHERE id=?", (comment.strip(), sheet_id))
        after = self.hydrate_sheet(sheet_id)
        self.audit(manager_id, "goal_sheet", sheet_id, "returned_for_rework", before, after, comment.strip())
        return after

    def add_progress(self, actor_id: int, goal_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        goal = self.get_goal(goal_id)
        sheet = self.fetchone("SELECT * FROM goal_sheets WHERE id=?", (goal["sheet_id"],))
        if sheet["user_id"] != actor_id:
            raise DomainError("Employees can only update their own progress", 403)
        if sheet["state"] not in {"locked", "unlocked"}:
            raise DomainError("Progress can be updated only after manager approval")

        quarter = payload.get("quarter")
        ensure_window_open(self.quarter_window(quarter))

        if goal.get("shared_goal_id"):
            shared = self.fetchone("SELECT * FROM shared_goals WHERE id=?", (goal["shared_goal_id"],))
            if shared["primary_owner_id"] != actor_id:
                raise DomainError("Only the shared goal primary owner can update linked progress", 403)

        validate_progress_payload(goal, payload)
        score = calculate_progress(goal, payload.get("actual_value"), payload.get("completion_date"))
        before = self.fetchone("SELECT * FROM progress_updates WHERE goal_id=? AND quarter=?", (goal_id, quarter))
        self.execute(
            """
            INSERT INTO progress_updates (
              goal_id, shared_goal_id, quarter, actual_value, completion_date, status, score, notes, created_by, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(goal_id, quarter) DO UPDATE SET
              actual_value=excluded.actual_value,
              completion_date=excluded.completion_date,
              status=excluded.status,
              score=excluded.score,
              notes=excluded.notes,
              updated_at=excluded.updated_at
            """,
            (
                goal_id,
                goal.get("shared_goal_id"),
                quarter,
                payload.get("actual_value"),
                payload.get("completion_date"),
                payload["status"],
                score,
                payload.get("notes", ""),
                actor_id,
                utc_now(),
            ),
        )

        if goal.get("shared_goal_id"):
            self.sync_shared_progress(goal["shared_goal_id"], goal_id, quarter, actor_id)

        after = self.fetchone("SELECT * FROM progress_updates WHERE goal_id=? AND quarter=?", (goal_id, quarter))
        self.audit(actor_id, "progress_update", after["id"], "upserted", before, after)
        return after

    def sync_shared_progress(self, shared_goal_id: int, source_goal_id: int, quarter: str, actor_id: int) -> None:
        source = self.fetchone("SELECT * FROM progress_updates WHERE goal_id=? AND quarter=?", (source_goal_id, quarter))
        linked_goals = self.fetchall("SELECT * FROM goals WHERE shared_goal_id=? AND id<>?", (shared_goal_id, source_goal_id))
        for linked in linked_goals:
            self.execute(
                """
                INSERT INTO progress_updates (
                  goal_id, shared_goal_id, quarter, actual_value, completion_date, status, score, notes, created_by, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(goal_id, quarter) DO UPDATE SET
                  actual_value=excluded.actual_value,
                  completion_date=excluded.completion_date,
                  status=excluded.status,
                  score=excluded.score,
                  notes=excluded.notes,
                  updated_at=excluded.updated_at
                """,
                (
                    linked["id"],
                    shared_goal_id,
                    quarter,
                    source["actual_value"],
                    source["completion_date"],
                    source["status"],
                    source["score"],
                    source["notes"],
                    actor_id,
                    utc_now(),
                ),
            )

    def add_checkin(self, manager_id: int, sheet_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        quarter = payload.get("quarter")
        comment = payload.get("comment", "").strip()
        if quarter not in {"q1", "q2", "q3", "q4"}:
            raise DomainError("Select a valid quarter")
        if not comment:
            raise DomainError("Check-in comment is required")

        sheet = self.fetchone(
            """
            SELECT gs.* FROM goal_sheets gs
            JOIN users u ON u.id = gs.user_id
            WHERE gs.id=? AND u.manager_id=?
            """,
            (sheet_id, manager_id),
        )
        if not sheet:
            raise DomainError("Goal sheet not found for this manager", 404)

        before = self.fetchone("SELECT * FROM checkins WHERE sheet_id=? AND quarter=?", (sheet_id, quarter))
        self.execute(
            """
            INSERT INTO checkins (sheet_id, manager_id, quarter, comment, created_at)
            VALUES (?,?,?,?,?)
            ON CONFLICT(sheet_id, quarter) DO UPDATE SET
              comment=excluded.comment,
              created_at=excluded.created_at
            """,
            (sheet_id, manager_id, quarter, comment, utc_now()),
        )
        after = self.fetchone("SELECT * FROM checkins WHERE sheet_id=? AND quarter=?", (sheet_id, quarter))
        self.audit(manager_id, "checkin", after["id"], "saved", before, after)
        return after

    def create_shared_goal(self, actor_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        recipients = payload.get("recipient_ids") or []
        if not recipients:
            raise DomainError("Select at least one employee for the shared goal")

        validate_goal_payload({**payload, "weightage": payload.get("default_weightage", 10)})
        cur = self.execute(
            """
            INSERT INTO shared_goals (
              thrust_area, title, description, uom_type, direction, target_value, target_date,
              primary_owner_id, created_by, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                payload["thrust_area"],
                payload["title"],
                payload.get("description", ""),
                payload["uom_type"],
                payload["direction"],
                payload.get("target_value"),
                payload.get("target_date"),
                int(payload["primary_owner_id"]),
                actor_id,
                utc_now(),
            ),
        )
        shared_id = cur.lastrowid

        for recipient_id in recipients:
            self.create_goal(actor_id, int(recipient_id), {
                "shared_goal_id": shared_id,
                "thrust_area": payload["thrust_area"],
                "title": payload["title"],
                "description": payload.get("description", ""),
                "uom_type": payload["uom_type"],
                "direction": payload["direction"],
                "target_value": payload.get("target_value"),
                "target_date": payload.get("target_date"),
                "weightage": payload.get("default_weightage", 10),
            })

        shared = self.fetchone("SELECT * FROM shared_goals WHERE id=?", (shared_id,))
        self.audit(actor_id, "shared_goal", shared_id, "created", None, {**shared, "recipient_ids": recipients})
        return shared

    def unlock_sheet(self, actor_id: int, sheet_id: int, reason: str) -> dict[str, Any]:
        if not reason.strip():
            raise DomainError("Unlock reason is required")
        before = self.hydrate_sheet(sheet_id)
        self.execute(
            "UPDATE goal_sheets SET state='unlocked', unlocked_at=?, unlock_reason=? WHERE id=?",
            (utc_now(), reason.strip(), sheet_id),
        )
        self.execute("UPDATE goals SET locked=0 WHERE sheet_id=?", (sheet_id,))
        after = self.hydrate_sheet(sheet_id)
        self.audit(actor_id, "goal_sheet", sheet_id, "admin_unlocked", before, after, reason.strip())
        return after

    def team_sheets(self, manager_id: int) -> list[dict[str, Any]]:
        rows = self.fetchall(
            """
            SELECT gs.id FROM goal_sheets gs
            JOIN users u ON u.id = gs.user_id
            WHERE u.manager_id=?
            ORDER BY u.name
            """,
            (manager_id,),
        )
        return [self.hydrate_sheet(row["id"]) for row in rows]

    def all_sheets(self) -> list[dict[str, Any]]:
        rows = self.fetchall("SELECT id FROM goal_sheets ORDER BY id")
        return [self.hydrate_sheet(row["id"]) for row in rows]

    def dashboard_metrics(self) -> dict[str, Any]:
        sheets = self.all_sheets()
        total = len(sheets)
        locked = sum(1 for sheet in sheets if sheet["state"] == "locked")
        submitted = sum(1 for sheet in sheets if sheet["state"] == "submitted")
        draft = sum(1 for sheet in sheets if sheet["state"] in {"draft", "returned", "unlocked"})
        checkins = self.fetchall("SELECT quarter, COUNT(*) AS count FROM checkins GROUP BY quarter")
        uom_distribution = self.fetchall("SELECT uom_type AS label, COUNT(*) AS count FROM goals GROUP BY uom_type ORDER BY count DESC")
        department_completion = self.fetchall(
            """
            SELECT
              u.department AS label,
              COUNT(gs.id) AS total,
              SUM(CASE WHEN gs.state='locked' THEN 1 ELSE 0 END) AS complete
            FROM goal_sheets gs
            JOIN users u ON u.id = gs.user_id
            GROUP BY u.department
            ORDER BY u.department
            """
        )
        manager_effectiveness = self.fetchall(
            """
            SELECT
              m.name AS label,
              COUNT(DISTINCT gs.id) AS team_sheets,
              COUNT(DISTINCT c.id) AS checkins
            FROM users m
            JOIN users e ON e.manager_id = m.id
            LEFT JOIN goal_sheets gs ON gs.user_id = e.id
            LEFT JOIN checkins c ON c.sheet_id = gs.id
            WHERE m.role='manager'
            GROUP BY m.id
            ORDER BY m.name
            """
        )
        return {
            "total_sheets": total,
            "locked_sheets": locked,
            "submitted_sheets": submitted,
            "draft_sheets": draft,
            "completion_rate": round((locked / total) * 100, 1) if total else 0,
            "checkins": checkins,
            "uom_distribution": uom_distribution,
            "department_completion": department_completion,
            "manager_effectiveness": manager_effectiveness,
        }

    def notification_preview(self, role: str) -> list[dict[str, Any]]:
        base = [
            {
                "channel": "Email",
                "event": "Goal sheet submitted",
                "audience": "Manager",
                "copy": "An employee has submitted goals and is waiting for your review.",
            },
            {
                "channel": "Teams",
                "event": "Approval reminder",
                "audience": "Manager",
                "copy": "A goal sheet has been pending for more than 2 days. Open the approval queue.",
            },
            {
                "channel": "Email",
                "event": "Quarterly check-in window",
                "audience": "Employee",
                "copy": "The current quarter window is open. Update planned vs actual achievement.",
            },
        ]
        if role == "employee":
            return [item for item in base if item["audience"] == "Employee"]
        if role == "manager":
            return [item for item in base if item["audience"] == "Manager"]
        return base

    def app_state(self, user: dict[str, Any]) -> dict[str, Any]:
        state: dict[str, Any] = {
            "user": user,
            "cycle": self.active_cycle(),
            "metrics": self.dashboard_metrics(),
            "employees": self.fetchall("SELECT id,name,email,role,title,department,manager_id FROM users WHERE role='employee' ORDER BY name"),
            "managers": self.fetchall("SELECT id,name,email,role,title,department FROM users WHERE role='manager' ORDER BY name"),
            "shared_goals": self.fetchall("SELECT * FROM shared_goals ORDER BY id DESC"),
            "notifications": self.notification_preview(user["role"]),
        }
        if user["role"] == "employee":
            sheet = self.get_sheet_for_user(user["id"])
            state["my_sheet"] = self.hydrate_sheet(sheet["id"])
        elif user["role"] == "manager":
            team = self.team_sheets(user["id"])
            state["team_sheets"] = team
            state["approvals"] = [sheet for sheet in team if sheet["state"] == "submitted"]
        else:
            state["all_sheets"] = self.all_sheets()
            state["audit_logs"] = self.audit_logs()
            state["escalation_rules"] = self.fetchall("SELECT * FROM escalation_rules ORDER BY id")
            state["escalation_events"] = self.fetchall(
                """
                SELECT ev.*, er.name AS rule_name, u.name AS employee_name
                FROM escalation_events ev
                JOIN escalation_rules er ON er.id = ev.rule_id
                LEFT JOIN users u ON u.id = ev.user_id
                ORDER BY ev.id DESC
                """
            )
        return state

    def audit_logs(self) -> list[dict[str, Any]]:
        return self.fetchall(
            """
            SELECT a.*, u.name AS actor_name
            FROM audit_logs a
            JOIN users u ON u.id = a.actor_id
            ORDER BY a.id DESC
            LIMIT 80
            """
        )

    def achievement_csv(self) -> str:
        rows = self.fetchall(
            """
            SELECT
              u.name AS employee,
              u.department,
              g.title,
              g.uom_type,
              g.weightage,
              g.target_value,
              g.target_date,
              p.quarter,
              p.actual_value,
              p.completion_date,
              p.status,
              p.score
            FROM goals g
            JOIN goal_sheets gs ON gs.id = g.sheet_id
            JOIN users u ON u.id = gs.user_id
            LEFT JOIN progress_updates p ON p.goal_id = g.id
            ORDER BY u.name, g.id, p.quarter
            """
        )
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=[
            "employee", "department", "title", "uom_type", "weightage", "target_value",
            "target_date", "quarter", "actual_value", "completion_date", "status", "score"
        ])
        writer.writeheader()
        writer.writerows(rows)
        return out.getvalue()
