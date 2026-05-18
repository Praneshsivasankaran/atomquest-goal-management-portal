from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.business import DomainError
from app.server import assert_manager_owns_goal, assert_manager_owns_sheet, current_demo_date
from app.storage import Store


class ServerRouteGuardTests(unittest.TestCase):
    def make_store(self) -> Store:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / "demo.sqlite3"
        store = Store(path)
        self.addCleanup(store.close)
        return store

    def test_manager_goal_guard_rejects_other_manager(self) -> None:
        store = self.make_store()
        other_manager = store.register_user({
            "name": "Other Manager",
            "email": "other.manager@example.com",
            "password": "demo123",
            "role": "manager",
        })
        sheet = store.get_sheet_for_user(1)
        goal = store.sheet_goals(sheet["id"])[0]

        assert_manager_owns_goal(store, 2, goal["id"])
        with self.assertRaises(DomainError) as ctx:
            assert_manager_owns_goal(store, other_manager["id"], goal["id"])

        self.assertEqual(ctx.exception.status, 404)
        self.assertIn("for this manager", ctx.exception.message)

    def test_manager_sheet_guard_rejects_other_manager(self) -> None:
        store = self.make_store()
        other_manager = store.register_user({
            "name": "Second Manager",
            "email": "second.manager@example.com",
            "password": "demo123",
            "role": "manager",
        })
        sheet = store.get_sheet_for_user(1)

        assert_manager_owns_sheet(store, 2, sheet["id"])
        with self.assertRaises(DomainError) as ctx:
            assert_manager_owns_sheet(store, other_manager["id"], sheet["id"])

        self.assertEqual(ctx.exception.status, 404)
        self.assertIn("for this manager", ctx.exception.message)

    def test_current_demo_date_uses_kolkata_timezone(self) -> None:
        try:
            kolkata = ZoneInfo("Asia/Kolkata")
        except ZoneInfoNotFoundError:
            kolkata = timezone(timedelta(hours=5, minutes=30))
        expected = datetime.now(kolkata).date().isoformat()

        self.assertEqual(current_demo_date(), expected)


if __name__ == "__main__":
    unittest.main()
