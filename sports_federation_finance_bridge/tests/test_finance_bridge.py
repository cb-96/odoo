from odoo.tests import TransactionCase
from odoo.exceptions import ValidationError


class TestFinanceBridge(TransactionCase):
    """Test cases for finance bridge module."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create test club
        cls.club = cls.env["federation.club"].create({
            "name": "Test Club",
            "code": "TC001",
        })

    def test_create_fee_type(self):
        """Test creating a fee type."""
        fee_type = self.env["federation.fee.type"].create({
            "name": "Test Fee",
            "code": "TESTFEE",
            "category": "registration",
            "default_amount": 100.00,
        })
        self.assertTrue(fee_type.id)
        self.assertEqual(fee_type.name, "Test Fee")
        self.assertEqual(fee_type.code, "TESTFEE")
        self.assertEqual(fee_type.category, "registration")
        self.assertEqual(fee_type.default_amount, 100.00)

    def test_create_finance_event_directly(self):
        """Test creating a finance event directly."""
        fee_type = self.env["federation.fee.type"].create({
            "name": "Test Fee",
            "code": "TESTFEE",
            "category": "registration",
            "default_amount": 100.00,
        })
        event = self.env["federation.finance.event"].create({
            "name": "Test Event",
            "fee_type_id": fee_type.id,
            "event_type": "charge",
            "amount": 100.00,
            "source_model": "federation.club",
            "source_res_id": self.club.id,
            "club_id": self.club.id,
        })
        self.assertTrue(event.id)
        self.assertEqual(event.name, "Test Event")
        self.assertEqual(event.event_type, "charge")
        self.assertEqual(event.amount, 100.00)
        self.assertEqual(event.state, "draft")

    def test_create_finance_event_from_source(self):
        """Test creating a finance event from source record."""
        fee_type = self.env["federation.fee.type"].create({
            "name": "Test Fee",
            "code": "TESTFEE",
            "category": "registration",
            "default_amount": 100.00,
        })
        event = self.env["federation.finance.event"].create_from_source(
            source_record=self.club,
            fee_type=fee_type,
        )
        self.assertTrue(event.id)
        self.assertEqual(event.source_model, "federation.club")
        self.assertEqual(event.source_res_id, self.club.id)
        self.assertEqual(event.club_id, self.club)
        self.assertEqual(event.amount, 100.00)

    def test_finance_event_amount_validation(self):
        """Test amount validation on finance event."""
        fee_type = self.env["federation.fee.type"].create({
            "name": "Test Fee",
            "code": "TESTFEE",
            "category": "registration",
            "default_amount": 100.00,
        })
        with self.assertRaises(ValidationError):
            self.env["federation.finance.event"].create({
                "name": "Test Event",
                "fee_type_id": fee_type.id,
                "event_type": "charge",
                "amount": -10.00,
                "source_model": "federation.club",
                "source_res_id": self.club.id,
            })

    def test_state_transitions(self):
        """Test state transitions on finance event."""
        fee_type = self.env["federation.fee.type"].create({
            "name": "Test Fee",
            "code": "TESTFEE",
            "category": "registration",
            "default_amount": 100.00,
        })
        event = self.env["federation.finance.event"].create({
            "name": "Test Event",
            "fee_type_id": fee_type.id,
            "event_type": "charge",
            "amount": 100.00,
            "source_model": "federation.club",
            "source_res_id": self.club.id,
        })
        self.assertEqual(event.state, "draft")

        # Confirm
        event.action_confirm()
        self.assertEqual(event.state, "confirmed")

        # Settle
        event.action_settle()
        self.assertEqual(event.state, "settled")

        # Cannot cancel settled
        with self.assertRaises(ValidationError):
            event.action_cancel()

    def test_cancel_from_draft(self):
        """Test cancelling from draft."""
        fee_type = self.env["federation.fee.type"].create({
            "name": "Test Fee",
            "code": "TESTFEE",
            "category": "registration",
            "default_amount": 100.00,
        })
        event = self.env["federation.finance.event"].create({
            "name": "Test Event",
            "fee_type_id": fee_type.id,
            "event_type": "charge",
            "amount": 100.00,
            "source_model": "federation.club",
            "source_res_id": self.club.id,
        })
        event.action_cancel()
        self.assertEqual(event.state, "cancelled")

    def test_cancel_from_confirmed(self):
        """Test cancelling from confirmed."""
        fee_type = self.env["federation.fee.type"].create({
            "name": "Test Fee",
            "code": "TESTFEE",
            "category": "registration",
            "default_amount": 100.00,
        })
        event = self.env["federation.finance.event"].create({
            "name": "Test Event",
            "fee_type_id": fee_type.id,
            "event_type": "charge",
            "amount": 100.00,
            "source_model": "federation.club",
            "source_res_id": self.club.id,
        })
        event.action_confirm()
        event.action_cancel()
        self.assertEqual(event.state, "cancelled")