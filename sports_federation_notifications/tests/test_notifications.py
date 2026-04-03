from odoo.tests import TransactionCase
from odoo.exceptions import ValidationError


class TestNotifications(TransactionCase):
    """Test cases for notification service."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create test club
        cls.club = cls.env["federation.club"].create({
            "name": "Test Club",
            "code": "TC001",
            "email": "test@example.com",
        })

    def test_log_creation(self):
        """Test creating a notification log."""
        log = self.env["federation.notification.log"].create({
            "name": "Test Log",
            "notification_type": "email",
            "state": "pending",
        })
        self.assertTrue(log.id)
        self.assertEqual(log.name, "Test Log")
        self.assertEqual(log.notification_type, "email")
        self.assertEqual(log.state, "pending")

    def test_send_email_template_creates_log(self):
        """Test that send_email_template creates a log entry."""
        service = self.env["federation.notification.service"]
        log = service.send_email_template(
            self.club,
            "sports_federation_notifications.template_federation_generic_contact",
            email_to="test@example.com",
            log_name="Test Email",
        )
        self.assertTrue(log.id)
        self.assertEqual(log.name, "Test Email")
        self.assertEqual(log.target_model, "federation.club")
        self.assertEqual(log.target_res_id, self.club.id)
        self.assertEqual(log.recipient_email, "test@example.com")
        self.assertEqual(log.notification_type, "email")
        self.assertIn(log.state, ("sent", "failed"))

    def test_create_activity(self):
        """Test creating an activity and log."""
        service = self.env["federation.notification.service"]
        user = self.env.ref("base.user_admin")
        log = service.create_activity(
            self.club,
            user.id,
            "Test Activity Summary",
            note="Test note",
        )
        self.assertTrue(log.id)
        self.assertEqual(log.name, "Test Activity Summary")
        self.assertEqual(log.notification_type, "activity")
        self.assertIn(log.state, ("sent", "failed"))

    def test_cron_method_runs_without_error(self):
        """Test that cron method runs without error."""
        service = self.env["federation.notification.service"]
        try:
            service._cron_placeholder_notification_scan()
        except Exception as e:
            self.fail(f"Cron method raised exception: {e}")