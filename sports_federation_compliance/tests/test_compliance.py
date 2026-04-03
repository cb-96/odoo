from odoo.tests import TransactionCase
from odoo.exceptions import ValidationError
from datetime import date, timedelta


class TestCompliance(TransactionCase):
    """Test cases for the sports_federation_compliance module."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create test club
        cls.club = cls.env["federation.club"].create({
            "name": "Test Club",
            "code": "TC001",
        })

        # Create test player
        cls.player = cls.env["federation.player"].create({
            "first_name": "John",
            "last_name": "Doe",
            "birth_date": "1990-01-01",
        })

        # Create test referee
        cls.referee = cls.env["federation.referee"].create({
            "name": "Jane Smith",
            "email": "jane@example.com",
        })

        # Create test venue
        cls.venue = cls.env["federation.venue"].create({
            "name": "Test Stadium",
            "city": "Test City",
        })

        # Create test requirement
        cls.requirement = cls.env["federation.document.requirement"].create({
            "name": "Club Registration",
            "code": "CLUB_REG",
            "target_model": "federation.club",
            "requires_expiry_date": True,
            "validity_days": 365,
        })

    def test_create_requirement(self):
        """Test creating a document requirement."""
        requirement = self.env["federation.document.requirement"].create({
            "name": "Player License",
            "code": "PLAYER_LIC",
            "target_model": "federation.player",
        })
        self.assertTrue(requirement.id)
        self.assertEqual(requirement.name, "Player License")
        self.assertEqual(requirement.target_model, "federation.player")

    def test_requirement_unique_code_target(self):
        """Test unique constraint on (code, target_model)."""
        with self.assertRaises(ValidationError):
            self.env["federation.document.requirement"].create({
                "name": "Duplicate Requirement",
                "code": "CLUB_REG",  # Same code as setUpClass
                "target_model": "federation.club",  # Same target_model
            })

    def test_submission_requires_single_target(self):
        """Test that exactly one target entity must be set."""
        # No target set
        with self.assertRaises(ValidationError):
            submission = self.env["federation.document.submission"].create({
                "name": "Test Submission",
                "requirement_id": self.requirement.id,
            })
            # Trigger constraint check
            submission._check_single_target()

        # Multiple targets set
        with self.assertRaises(ValidationError):
            submission = self.env["federation.document.submission"].create({
                "name": "Test Submission",
                "requirement_id": self.requirement.id,
                "club_id": self.club.id,
                "player_id": self.player.id,
            })
            # Trigger constraint check
            submission._check_single_target()

    def test_submission_target_matches_requirement_model(self):
        """Test that target matches requirement.target_model."""
        # Requirement is for club, but setting player should fail
        with self.assertRaises(ValidationError):
            submission = self.env["federation.document.submission"].create({
                "name": "Test Submission",
                "requirement_id": self.requirement.id,
                "player_id": self.player.id,  # Wrong target for club requirement
            })
            # Trigger constraint check
            submission._check_target_matches_requirement()

        # Correct target should work
        submission = self.env["federation.document.submission"].create({
            "name": "Test Submission",
            "requirement_id": self.requirement.id,
            "club_id": self.club.id,
        })
        self.assertEqual(submission.target_model, "federation.club")
        self.assertEqual(submission.club_id, self.club)

    def test_submission_date_validation(self):
        """Test that expiry_date >= issue_date if both set."""
        with self.assertRaises(ValidationError):
            self.env["federation.document.submission"].create({
                "name": "Test Submission",
                "requirement_id": self.requirement.id,
                "club_id": self.club.id,
                "issue_date": date.today(),
                "expiry_date": date.today() - timedelta(days=1),  # Before issue date
            })

    def test_submission_workflow(self):
        """Test submission workflow: draft -> submitted -> approved."""
        submission = self.env["federation.document.submission"].create({
            "name": "Test Submission",
            "requirement_id": self.requirement.id,
            "club_id": self.club.id,
        })
        self.assertEqual(submission.status, "draft")

        # Submit
        submission.action_submit()
        self.assertEqual(submission.status, "submitted")

        # Approve
        submission.action_approve()
        self.assertEqual(submission.status, "approved")
        self.assertTrue(submission.reviewer_id)
        self.assertTrue(submission.reviewed_on)

    def test_submission_reject(self):
        """Test submission rejection."""
        submission = self.env["federation.document.submission"].create({
            "name": "Test Submission",
            "requirement_id": self.requirement.id,
            "club_id": self.club.id,
        })
        submission.action_submit()
        submission.action_reject()
        self.assertEqual(submission.status, "rejected")

    def test_submission_request_replacement(self):
        """Test requesting replacement for approved document."""
        submission = self.env["federation.document.submission"].create({
            "name": "Test Submission",
            "requirement_id": self.requirement.id,
            "club_id": self.club.id,
        })
        submission.action_submit()
        submission.action_approve()
        submission.action_request_replacement()
        self.assertEqual(submission.status, "replacement_requested")

    def test_check_detects_missing_document(self):
        """Test that compliance check detects missing document."""
        checks = self.env["federation.compliance.check"].recompute_checks_for_target(
            self.club, "federation.club"
        )
        self.assertTrue(len(checks) > 0)
        missing_check = checks.filtered(lambda c: c.status == "missing")
        self.assertTrue(missing_check)
        self.assertEqual(missing_check.note, "No submission found")

    def test_check_detects_valid_approved_document(self):
        """Test that compliance check detects valid approved document."""
        # Create and approve submission
        submission = self.env["federation.document.submission"].create({
            "name": "Test Submission",
            "requirement_id": self.requirement.id,
            "club_id": self.club.id,
            "issue_date": date.today(),
            "expiry_date": date.today() + timedelta(days=365),
        })
        submission.action_submit()
        submission.action_approve()

        # Recompute checks
        checks = self.env["federation.compliance.check"].recompute_checks_for_target(
            self.club, "federation.club"
        )
        compliant_check = checks.filtered(lambda c: c.status == "compliant")
        self.assertTrue(compliant_check)
        self.assertEqual(compliant_check.note, "Document is valid")
        self.assertEqual(compliant_check.submission_id, submission)

    def test_check_detects_expired_document(self):
        """Test that compliance check detects expired document."""
        # Create and approve submission with past expiry date
        submission = self.env["federation.document.submission"].create({
            "name": "Test Submission",
            "requirement_id": self.requirement.id,
            "club_id": self.club.id,
            "issue_date": date.today() - timedelta(days=400),
            "expiry_date": date.today() - timedelta(days=1),  # Expired
        })
        submission.action_submit()
        submission.action_approve()

        # Recompute checks
        checks = self.env["federation.compliance.check"].recompute_checks_for_target(
            self.club, "federation.club"
        )
        expired_check = checks.filtered(lambda c: c.status == "expired")
        self.assertTrue(expired_check)
        self.assertEqual(expired_check.note, "Document has expired")

    def test_check_single_target(self):
        """Test that compliance check requires exactly one target."""
        with self.assertRaises(ValidationError):
            self.env["federation.compliance.check"].create({
                "name": "Test Check",
                "target_model": "federation.club",
                "status": "compliant",
                "requirement_id": self.requirement.id,
                # No target set
            })

    def test_is_expired_helper(self):
        """Test the is_expired helper method."""
        submission = self.env["federation.document.submission"].create({
            "name": "Test Submission",
            "requirement_id": self.requirement.id,
            "club_id": self.club.id,
            "expiry_date": date.today() - timedelta(days=1),
        })
        self.assertTrue(submission.is_expired())

        submission2 = self.env["federation.document.submission"].create({
            "name": "Test Submission 2",
            "requirement_id": self.requirement.id,
            "club_id": self.club.id,
            "expiry_date": date.today() + timedelta(days=30),
        })
        self.assertFalse(submission2.is_expired())

        submission3 = self.env["federation.document.submission"].create({
            "name": "Test Submission 3",
            "requirement_id": self.requirement.id,
            "club_id": self.club.id,
            # No expiry_date
        })
        self.assertFalse(submission3.is_expired())