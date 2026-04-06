from odoo import api, fields, models


class FederationNotificationLog(models.Model):
    _name = "federation.notification.log"
    _description = "Federation Notification Log"
    _order = "create_date desc"

    name = fields.Char(string="Name", required=True)
    target_model = fields.Char(string="Target Model")
    target_res_id = fields.Integer(string="Target Record ID")
    recipient_partner_id = fields.Many2one(
        "res.partner",
        string="Recipient Partner",
        ondelete="set null",
    )
    recipient_email = fields.Char(string="Recipient Email")
    notification_type = fields.Selection(
        [
            ("email", "Email"),
            ("activity", "Activity"),
            ("other", "Other"),
        ],
        string="Notification Type",
        required=True,
    )
    template_xmlid = fields.Char(string="Template XML ID")
    sent_on = fields.Datetime(string="Sent On")
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("sent", "Sent"),
            ("failed", "Failed"),
        ],
        string="State",
        default="pending",
        required=True,
    )
    message = fields.Text(string="Message")

    @api.model
    def _cron_notification_scan(self):
        """Delegate to the notification service cron method."""
        self.env["federation.notification.service"]._cron_placeholder_notification_scan()