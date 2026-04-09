from odoo.tests import TransactionCase
from odoo.exceptions import ValidationError


class TestResultControl(TransactionCase):
    """Test cases for result control workflow."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create test data
        cls.club_home = cls.env["federation.club"].create({
            "name": "Home Club",
            "code": "HOME",
        })
        cls.club_away = cls.env["federation.club"].create({
            "name": "Away Club",
            "code": "AWAY",
        })
        cls.team_home = cls.env["federation.team"].create({
            "name": "Home Team",
            "club_id": cls.club_home.id,
        })
        cls.team_away = cls.env["federation.team"].create({
            "name": "Away Team",
            "club_id": cls.club_away.id,
        })
        cls.season = cls.env["federation.season"].create({
            "name": "Test Season",
            "code": "TS2024",
            "date_start": "2024-09-01",
            "date_end": "2025-06-30",
        })
        cls.tournament = cls.env["federation.tournament"].create({
            "name": "Test Tournament",
            "season_id": cls.season.id,
            "date_start": "2024-09-01",
        })
        cls.match = cls.env["federation.match"].create({
            "tournament_id": cls.tournament.id,
            "home_team_id": cls.team_home.id,
            "away_team_id": cls.team_away.id,
            "home_score": 2,
            "away_score": 1,
        })

    def test_submit_result(self):
        """Test submitting a result from draft."""
        self.assertEqual(self.match.result_state, "draft")
        self.match.action_submit_result()
        self.assertEqual(self.match.result_state, "submitted")
        self.assertTrue(self.match.result_submitted_by_id)
        self.assertTrue(self.match.result_submitted_on)

    def test_verify_result(self):
        """Test verifying a submitted result."""
        self.match.action_submit_result()
        self.assertEqual(self.match.result_state, "submitted")
        self.match.action_verify_result()
        self.assertEqual(self.match.result_state, "verified")
        self.assertTrue(self.match.result_verified_by_id)
        self.assertTrue(self.match.result_verified_on)

    def test_approve_result_sets_official_flag(self):
        """Test approving a result sets include_in_official_standings."""
        self.match.action_submit_result()
        self.match.action_verify_result()
        self.assertFalse(self.match.include_in_official_standings)
        self.match.action_approve_result()
        self.assertEqual(self.match.result_state, "approved")
        self.assertTrue(self.match.include_in_official_standings)
        self.assertTrue(self.match.result_approved_by_id)
        self.assertTrue(self.match.result_approved_on)

    def test_contest_requires_reason(self):
        """Test contesting requires a reason."""
        self.match.action_submit_result()
        with self.assertRaises(ValidationError):
            self.match.action_contest_result()

    def test_contest_sets_flags(self):
        """Test contesting sets correct flags."""
        self.match.action_submit_result()
        self.match.result_contest_reason = "Score disputed"
        self.match.action_contest_result()
        self.assertEqual(self.match.result_state, "contested")
        self.assertFalse(self.match.include_in_official_standings)

    def test_correct_requires_reason(self):
        """Test correcting requires a reason."""
        self.match.action_submit_result()
        self.match.result_contest_reason = "Score disputed"
        self.match.action_contest_result()
        with self.assertRaises(ValidationError):
            self.match.action_correct_result()

    def test_correct_sets_flags(self):
        """Test correcting sets correct flags."""
        self.match.action_submit_result()
        self.match.result_contest_reason = "Score disputed"
        self.match.action_contest_result()
        self.match.result_correction_reason = "Score updated"
        self.match.action_correct_result()
        self.assertEqual(self.match.result_state, "corrected")
        self.assertFalse(self.match.include_in_official_standings)

    def test_reset_to_draft(self):
        """Test resetting to draft."""
        self.match.action_submit_result()
        self.match.action_verify_result()
        self.match.action_approve_result()
        self.assertEqual(self.match.result_state, "approved")
        self.match.action_reset_result_to_draft()
        self.assertEqual(self.match.result_state, "draft")
        self.assertFalse(self.match.include_in_official_standings)

    def test_invalid_transition_raises(self):
        """Test invalid transitions raise ValidationError."""
        # Cannot verify from draft
        with self.assertRaises(ValidationError):
            self.match.action_verify_result()
        # Cannot approve from draft
        with self.assertRaises(ValidationError):
            self.match.action_approve_result()
        # Cannot submit from submitted
        self.match.action_submit_result()
        with self.assertRaises(ValidationError):
            self.match.action_submit_result()