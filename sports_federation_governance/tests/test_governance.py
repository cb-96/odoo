from odoo.tests import TransactionCase
from odoo.exceptions import ValidationError
from odoo.addons.sports_federation_governance.workflow_states import (
    OVERRIDE_DECISION_SELECTION,
    OVERRIDE_REQUEST_STATE_APPROVED,
    OVERRIDE_REQUEST_STATE_DRAFT,
    OVERRIDE_REQUEST_STATE_REJECTED,
    OVERRIDE_REQUEST_STATE_SELECTION,
    OVERRIDE_REQUEST_STATE_SUBMITTED,
)


class TestGovernance(TransactionCase):
    """Test cases for governance module."""

    @classmethod
    def setUpClass(cls):
        """Set up shared test data for the test case."""
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
        self.assertEqual(request.state, OVERRIDE_REQUEST_STATE_DRAFT)
        self.assertEqual(request.requested_by_id, self.env.user)

    def test_override_models_use_shared_state_selections(self):
        """Governance workflow selections should reuse the shared helper module."""
        self.assertEqual(
            self.env["federation.override.request"].STATE_SELECTION,
            OVERRIDE_REQUEST_STATE_SELECTION,
        )
        self.assertEqual(
            self.env["federation.override.decision"].DECISION_SELECTION,
            OVERRIDE_DECISION_SELECTION,
        )

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
        self.assertEqual(request.state, OVERRIDE_REQUEST_STATE_SUBMITTED)

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
        self.assertEqual(request.state, OVERRIDE_REQUEST_STATE_APPROVED)
        self.assertTrue(request.decision_ids)
        self.assertEqual(request.decision_ids[0].decision, OVERRIDE_REQUEST_STATE_APPROVED)

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
        self.assertEqual(request.state, OVERRIDE_REQUEST_STATE_REJECTED)
        self.assertTrue(request.decision_ids)
        self.assertEqual(request.decision_ids[0].decision, OVERRIDE_REQUEST_STATE_REJECTED)

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
        self.assertTrue(request.outcome_ids)
        self.assertEqual(request.outcome_ids[0].outcome, "implemented")

    def test_override_outcome_records_request_snapshot(self):
        """Test that override outcome records request snapshot."""
        request = self.env["federation.override.request"].create({
            "name": "Tracked Request",
            "request_type": "standing_adjustment",
            "target_model": "federation.tournament",
            "target_res_id": 4,
            "reason": "Track Year 4 outcome logging.",
        })

        outcome = self.env["federation.override.outcome"].create({
            "request_id": request.id,
            "outcome": "effective",
            "note": "The override achieved the intended effect.",
        })

        self.assertEqual(outcome.request_type, "standing_adjustment")
        self.assertEqual(outcome.target_model, "federation.tournament")
        self.assertEqual(outcome.target_res_id, 4)
        self.assertEqual(outcome.request_state, OVERRIDE_REQUEST_STATE_DRAFT)

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