from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class FrontendStaticTests(unittest.TestCase):
    def read_app_js(self) -> str:
        return (ROOT / "public" / "app.js").read_text(encoding="utf-8")

    def test_admin_demo_mode_button_is_promoted_to_callout(self) -> None:
        app_js = self.read_app_js()
        admin_section = app_js.split("function renderAdmin() {", 1)[1].split("function renderReportCenter()", 1)[0]
        hero_actions = admin_section.split("actions: `", 1)[1].split("`,", 1)[0]

        self.assertIn("demo-callout", admin_section)
        self.assertIn("Open all quarters for live demo", admin_section)
        self.assertIn("Temporarily opens Q1-Q4 windows so you can capture progress now.", admin_section)
        self.assertNotIn("demo-mode", hero_actions)

    def test_admin_empty_state_points_to_seed_command(self) -> None:
        app_js = self.read_app_js()

        self.assertIn("Demo data isn't loaded", app_js)
        self.assertIn("python app/server.py --seed-only", app_js)


if __name__ == "__main__":
    unittest.main()
