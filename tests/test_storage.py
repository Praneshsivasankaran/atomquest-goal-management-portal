from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.business import DomainError
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


if __name__ == "__main__":
    unittest.main()

