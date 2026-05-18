from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.business import DomainError, MAX_GOALS_ERROR, MAX_GOALS_PER_EMPLOYEE
from app.storage import Store


class StorageWorkflowTests(unittest.TestCase):
    def make_store(self) -> Store:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / "demo.sqlite3"
        store = Store(path)
        store.execute("UPDATE cycle_windows SET opens_on='2000-01-01', closes_on='2999-12-31'")
        self.addCleanup(store.close)
        return store

    def test_manager_approval_locks_employee_goals(self) -> None:
        store = self.make_store()

        submitted = store.submit_sheet(1)
        approved = store.approve_sheet(2, submitted["id"])

        self.assertEqual(approved["state"], "locked")
        with self.assertRaises(DomainError):
            store.update_goal(1, approved["goals"][0]["id"], {"weightage": 50})

    def test_admin_unlock_allows_employee_edits_again(self) -> None:
        store = self.make_store()

        submitted = store.submit_sheet(1)
        approved = store.approve_sheet(2, submitted["id"])
        unlocked = store.unlock_sheet(3, approved["id"], "Need to correct a target before Q1")
        updated = store.update_goal(1, unlocked["goals"][0]["id"], {"weightage": 40})

        self.assertEqual(unlocked["state"], "unlocked")
        self.assertEqual(updated["weightage"], 40)

    def test_create_goal_uses_shared_max_goal_constant(self) -> None:
        store = self.make_store()
        user = store.register_user({
            "name": "Limit Tester",
            "email": "limit.tester@example.com",
            "password": "demo123",
            "role": "employee",
        })

        for index in range(MAX_GOALS_PER_EMPLOYEE):
            store.create_goal(user["id"], user["id"], {
                "thrust_area": "Execution",
                "title": f"Goal {index + 1}",
                "description": "Keep the cap behavior predictable.",
                "uom_type": "numeric",
                "direction": "min",
                "target_value": 100,
                "weightage": 10,
            })

        with self.assertRaises(DomainError) as ctx:
            store.create_goal(user["id"], user["id"], {
                "thrust_area": "Execution",
                "title": "Goal over limit",
                "description": "This one should not be accepted.",
                "uom_type": "numeric",
                "direction": "min",
                "target_value": 100,
                "weightage": 10,
            })

        self.assertEqual(ctx.exception.message, MAX_GOALS_ERROR)

    def test_shared_goal_progress_syncs_to_linked_recipients(self) -> None:
        store = self.make_store()
        shared = store.create_shared_goal(3, {
            "thrust_area": "Customer Quality",
            "title": "Reduce customer complaints",
            "description": "Shared KPI from HR",
            "uom_type": "percentage",
            "direction": "max",
            "target_value": 20,
            "default_weightage": 10,
            "primary_owner_id": 1,
            "recipient_ids": [1, 5],
        })
        store.execute("UPDATE goal_sheets SET state='locked', locked_at='2026-05-01T00:00:00Z' WHERE user_id IN (1,5)")
        linked = store.fetchall("SELECT * FROM goals WHERE shared_goal_id=? ORDER BY sheet_id", (shared["id"],))

        store.add_progress(1, linked[0]["id"], {
            "quarter": "q1",
            "actual_value": 10,
            "status": "completed",
            "notes": "Complaints are down across the shared cohort.",
        })

        synced = store.fetchall("SELECT * FROM progress_updates WHERE shared_goal_id=? ORDER BY goal_id", (shared["id"],))
        self.assertEqual(len(synced), 2)
        self.assertTrue(all(row["score"] == 100 for row in synced))

    def test_audit_log_records_workflow_actions(self) -> None:
        store = self.make_store()

        submitted = store.submit_sheet(1)
        store.approve_sheet(2, submitted["id"])
        logs = store.audit_logs()

        actions = {log["action"] for log in logs}
        self.assertIn("submitted", actions)
        self.assertIn("approved_and_locked", actions)

    def test_approve_sheet_revalidates_after_manager_edits(self) -> None:
        store = self.make_store()

        submitted = store.submit_sheet(1)
        store.update_goal(2, submitted["goals"][0]["id"], {"weightage": 45}, manager_edit=True)

        with self.assertRaises(DomainError) as ctx:
            store.approve_sheet(2, submitted["id"])

        self.assertIn("exactly 100", ctx.exception.message)

    def test_goal_suggestions_use_employee_context(self) -> None:
        store = self.make_store()

        suggestions = store.goal_suggestions(1)

        self.assertGreaterEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0]["thrust_area"], "Revenue Growth")
        self.assertIn("fit_reason", suggestions[0])

    def test_demo_mode_opens_all_cycle_windows(self) -> None:
        store = self.make_store()

        windows = store.activate_demo_windows(3, "2026-05-18")

        self.assertTrue(all(window["opens_on"] <= "2026-05-18" for window in windows))
        self.assertTrue(all(window["closes_on"] >= "2026-05-18" for window in windows))

    def test_seeded_metrics_include_quarter_trends(self) -> None:
        store = self.make_store()

        metrics = store.dashboard_metrics()

        self.assertGreaterEqual(len(metrics["quarter_trends"]), 1)

    def test_signup_creates_employee_goal_sheet(self) -> None:
        store = self.make_store()

        user = store.register_user({
            "name": "New Employee",
            "email": "new.employee@example.com",
            "password": "demo123",
            "role": "employee",
            "department": "Sales",
            "title": "Sales Associate",
        })
        sheet = store.get_sheet_for_user(user["id"])

        self.assertEqual(user["role"], "employee")
        self.assertEqual(sheet["state"], "draft")

    def test_signup_rejects_duplicate_email(self) -> None:
        store = self.make_store()

        with self.assertRaises(DomainError):
            store.register_user({
                "name": "Duplicate",
                "email": "employee@demo.com",
                "password": "demo123",
                "role": "employee",
            })

    def test_admin_can_update_org_hierarchy(self) -> None:
        store = self.make_store()

        updated = store.update_user(3, 5, {
            "role": "employee",
            "department": "Product",
            "title": "Product Operations Analyst",
            "manager_id": 2,
        })

        self.assertEqual(updated["department"], "Product")
        self.assertEqual(updated["manager_id"], 2)

    def test_achievement_xlsx_returns_workbook_bytes(self) -> None:
        store = self.make_store()

        workbook = store.achievement_xlsx()

        self.assertTrue(workbook.startswith(b"PK"))
        self.assertIn(b"xl/worksheets/sheet1.xml", workbook)

    def test_login_migrates_legacy_sha256_to_scrypt(self) -> None:
        store = self.make_store()
        # Force-rewrite the demo user's hash back to legacy SHA-256 (as if from an
        # older deployment) so we can assert the migration on login works.
        from app.storage import legacy_sha256
        store.execute(
            "UPDATE users SET password_hash=? WHERE email='employee@demo.com'",
            (legacy_sha256("demo123"),),
        )
        # Login succeeds with the legacy hash.
        store.authenticate("employee@demo.com", "demo123")
        # Hash is now upgraded.
        row = store.fetchone("SELECT password_hash FROM users WHERE email='employee@demo.com'")
        self.assertTrue(row["password_hash"].startswith("scrypt$"))

    def test_seed_health_requires_core_demo_roles(self) -> None:
        store = self.make_store()
        store.execute("DELETE FROM users WHERE role='admin'")

        with self.assertRaises(RuntimeError) as ctx:
            store.assert_seed_health()

        self.assertIn("admin", str(ctx.exception))

    def test_seed_health_requires_demo_sheet_states(self) -> None:
        store = self.make_store()
        store.execute("UPDATE goal_sheets SET state='draft' WHERE state='locked'")

        with self.assertRaises(RuntimeError) as ctx:
            store.assert_seed_health()

        self.assertIn("locked", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
