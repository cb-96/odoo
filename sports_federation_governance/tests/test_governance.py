from odoo.tests import TransactionCase
from odoo.exceptions import ValidationError


class TestGovernance(TransactionCase):
    """Test cases for governance module."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create test user
        cls.user = cls.env.ref("base.user_admin")

    def test_create_override_request(self):
        """Test creating an override request."""
        request = self.env["federation.override.request"].create({
            "name": "Test Request",
            "request_type": "manual_seeding",
            "target_model": "federation.tournament",
            "target_res_id": 1,
            "reason": "Test reason for override",
        })
        self.assertTrue(request.id)
        self.assertEqual(request.state, "draft")
        self.assertEqual(request.requested_by_id, self.env.user)

    def test_submit_override_request(self):
        """Test submitting an override request."""
        request = self.env["federation.override.request"].create({
            "name": "Test Request",
            "request_type": "manual_seeding",
            "target_model": "federation.tournament",
            "target_res_id": 1,
            "reason": "Test reason",
        })
        request.action_submit()
        self.assertEqual(request.state, "submitted")

    def test_approve_creates_decision(self):
        """Test approving creates a decision record."""
        request = self.env["federation.override.request"].create({
            "name": "Test Request",
            "request_type": "eligibility_waiver",
            "target_model": "federation.player",
            "target_res_id": 1,
            "reason": "Test reason",
        })
        request.action_submit()
        request.action_approve()
        self.assertEqual(request.state, "approved")
        self.assertTrue(request.decision_ids)
        self.assertEqual(request.decision_ids[0].decision, "approved")

    def test_reject_creates_decision(self):
        """Test rejecting creates a decision record."""
        request = self.env["federation.override.request"].create({
            "name": "Test Request",
            "request_type": "late_registration",
            "target_model": "federation.team",
            "target_res_id": 1,
            "reason": "Test reason",
        })
        request.action_submit()
        request.action_reject()
        self.assertEqual(request.state, "rejected")
        self.assertTrue(request.decision_ids)
        self.assertEqual(request.decision_ids[0].decision, "rejected")

    def test_mark_implemented(self):
        """Test marking request as implemented."""
        request = self.env["federation.override.request"].create({
            "name": "Test Request",
            "request_type": "result_correction",
            "target_model": "federation.match",
            "target_res_id": 1,
            "reason": "Test reason",
        })
        request.action_submit()
        request.action_approve()
        request.action_mark_implemented()
        self.assertEqual(request.state, "implemented")

    def test_target_validation(self):
        """Test target validation constraints."""
        # Test empty target_model
        with self.assertRaises(ValidationError):
            self.env["federation.override.request"].create({
                "name": "Test Request",
                "request_type": "manual_seeding",
                "target_model": "",
                "target_res_id": 1,
                "reason": "Test reason",
            })

        # Test target_res_id <= 0
        with self.assertRaises(ValidationError):
            self.env["federation.override.request"].create({
                "name": "Test Request",
                "request_type": "manual_seeding",
                "target_model": "federation.tournament",
                "target_res_id": 0,
                "reason": "Test reason",
            })

    def test_empty_reason_validation(self):
        """Test empty reason validation."""
        with self.assertRaises(ValidationError):
            self.env["federation.override.request"].create({
                "name": "Test Request",
                "request_type": "manual_seeding",
                "target_model": "federation.tournament",
                "target_res_id": 1,
                "reason": "",
            })