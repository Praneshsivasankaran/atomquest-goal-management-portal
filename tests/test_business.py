from __future__ import annotations

import unittest

from app.business import DomainError, calculate_progress, validate_goal_sheet


class BusinessRuleTests(unittest.TestCase):
    def test_goal_sheet_requires_exact_weightage(self) -> None:
        goals = [{"weightage": 20}, {"weightage": 30}, {"weightage": 20}]

        with self.assertRaises(DomainError) as ctx:
            validate_goal_sheet(goals)

        self.assertIn("exactly 100", ctx.exception.message)

    def test_goal_sheet_accepts_valid_distribution(self) -> None:
        validate_goal_sheet([
            {"weightage": 40},
            {"weightage": 30},
            {"weightage": 30},
        ])

    def test_progress_scoring_for_higher_is_better(self) -> None:
        score = calculate_progress({"uom_type": "numeric", "direction": "min", "target_value": 100}, actual_value=75)
        self.assertEqual(score, 75)

    def test_progress_scoring_for_lower_is_better(self) -> None:
        score = calculate_progress({"uom_type": "numeric", "direction": "max", "target_value": 20}, actual_value=25)
        self.assertEqual(score, 80)

    def test_timeline_goal_scores_by_deadline(self) -> None:
        early = calculate_progress({"uom_type": "timeline", "direction": "timeline", "target_date": "2026-06-01"}, completion_date="2026-05-30")
        late = calculate_progress({"uom_type": "timeline", "direction": "timeline", "target_date": "2026-06-01"}, completion_date="2026-06-02")
        self.assertEqual(early, 100)
        self.assertEqual(late, 0)

    def test_zero_goal_scores_only_at_zero(self) -> None:
        self.assertEqual(calculate_progress({"uom_type": "zero", "direction": "zero", "target_value": 0}, actual_value=0), 100)
        self.assertEqual(calculate_progress({"uom_type": "zero", "direction": "zero", "target_value": 0}, actual_value=1), 0)


if __name__ == "__main__":
    unittest.main()

