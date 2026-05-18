from __future__ import annotations

import unittest

from app.business import DomainError, MAX_GOALS_ERROR, MAX_GOALS_PER_EMPLOYEE, calculate_progress, validate_goal_sheet


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

    def test_goal_sheet_enforces_shared_max_goal_constant(self) -> None:
        over_max = [{"weightage": 10} for _ in range(MAX_GOALS_PER_EMPLOYEE - 1)] + [{"weightage": 30}]

        with self.assertRaises(DomainError) as ctx:
            validate_goal_sheet(over_max)

        self.assertEqual(ctx.exception.message, MAX_GOALS_ERROR)

    def test_goal_sheet_uses_decimal_weightage_total(self) -> None:
        validate_goal_sheet([
            {"weightage": "33.33"},
            {"weightage": "33.33"},
            {"weightage": "33.34"},
        ])

        with self.assertRaises(DomainError) as ctx:
            validate_goal_sheet([
                {"weightage": "33.33"},
                {"weightage": "33.33"},
                {"weightage": "33.33"},
            ])

        self.assertIn("99.99", ctx.exception.message)

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


class AuthSecurityTests(unittest.TestCase):
    def test_password_hash_uses_scrypt_format(self) -> None:
        from app.auth import hash_password
        stored = hash_password("demo123")
        self.assertTrue(stored.startswith("scrypt$"))
        # Per-user salt means the same password produces a different hash each time.
        self.assertNotEqual(stored, hash_password("demo123"))

    def test_verify_password_accepts_legacy_sha256(self) -> None:
        import hashlib
        from app.auth import verify_password, needs_password_upgrade
        legacy = hashlib.sha256(b"demo123").hexdigest()
        self.assertTrue(verify_password("demo123", legacy))
        self.assertFalse(verify_password("wrong", legacy))
        self.assertTrue(needs_password_upgrade(legacy))

    def test_verify_password_rejects_corrupt_scrypt(self) -> None:
        from app.auth import verify_password
        self.assertFalse(verify_password("anything", "scrypt$not-hex$not-hex"))

    def test_assert_secret_is_safe_blocks_default_on_public_host(self) -> None:
        from app.auth import assert_secret_is_safe
        with self.assertRaises(RuntimeError):
            assert_secret_is_safe("0.0.0.0")

    def test_assert_secret_is_safe_allows_localhost(self) -> None:
        from app.auth import assert_secret_is_safe
        assert_secret_is_safe("127.0.0.1")
        assert_secret_is_safe("localhost")


class AuthRateLimitTests(unittest.TestCase):
    def setUp(self) -> None:
        from app.server import _auth_attempts
        _auth_attempts.clear()

    def test_login_rate_limited_after_five_attempts(self) -> None:
        from app.server import hit_auth_rate_limit, AUTH_RATE_LIMIT_MAX_HITS
        ip = "203.0.113.7"
        for _ in range(AUTH_RATE_LIMIT_MAX_HITS):
            self.assertEqual(hit_auth_rate_limit(ip), 0)
        retry = hit_auth_rate_limit(ip)
        self.assertGreater(retry, 0)


if __name__ == "__main__":
    unittest.main()
