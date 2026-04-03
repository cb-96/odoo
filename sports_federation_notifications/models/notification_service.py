from odoo import api, fields, models


class FederationNotificationService(models.AbstractModel):
    """Abstract service providing reusable notification helpers.

    Implemented as AbstractModel so it can be inherited by other modules
    without creating a concrete table. This keeps the service lightweight
    and allows future extensions.
    """

    _name = "federation.notification.service"
    _description = "Federation Notification Service"

    def send_email_template(self, record, template_xmlid, partner=None, email_to=None, log_name=None):
        """Send an email using a mail.template and create a log entry.

        Args:
            record: The target record for the template.
            template_xmlid: The XML ID of the mail.template (e.g., 'module_name.template_xxx').
            partner: Optional res.partner record for recipient.
            email_to: Optional email address string if no partner.
            log_name: Optional name for the log entry.

        Returns:
            The created notification log record.
        """
        Log = self.env["federation.notification.log"]
        log_vals = {
            "name": log_name or f"Email: {template_xmlid}",
            "target_model": record._name,
            "target_res_id": record.id,
            "notification_type": "email",
            "template_xmlid": template_xmlid,
            "state": "pending",
        }
        if partner:
            log_vals["recipient_partner_id"] = partner.id
            log_vals["recipient_email"] = partner.email
        elif email_to:
            log_vals["recipient_email"] = email_to

        log = Log.create(log_vals)

        try:
            template = self.env.ref(template_xmlid, raise_if_not_found=False)
            if not template:
                log.write({
                    "state": "failed",
                    "message": f"Template '{template_xmlid}' not found.",
                })
                return log

            if partner:
                template.send_mail(record.id, force_send=True, email_values={"recipient_ids": [(6, 0, [partner.id])]})
            elif email_to:
                template.send_mail(record.id, force_send=True, email_values={"email_to": email_to})
            else:
                template.send_mail(record.id, force_send=True)

            log.write({
                "state": "sent",
                "sent_on": fields.Datetime.now(),
            })
        except Exception as e:
            log.write({
                "state": "failed",
                "message": str(e),
            })

        return log

    def create_activity(self, record, user_id, summary, note=None, activity_type_xmlid="mail.mail_activity_data_todo"):
        """Create a mail.activity and log it.

        Args:
            record: The target record for the activity.
            user_id: The res.users ID to assign the activity to.
            summary: Activity summary string.
            note: Optional HTML note.
            activity_type_xmlid: XML ID for activity type (default: todo).

        Returns:
            The created notification log record.
        """
        Log = self.env["federation.notification.log"]
        activity_type = self.env.ref(activity_type_xmlid, raise_if_not_found=False)

        log_vals = {
            "name": summary,
            "target_model": record._name,
            "target_res_id": record.id,
            "notification_type": "activity",
            "state": "pending",
        }

        log = Log.create(log_vals)

        try:
            self.env["mail.activity"].create({
                "res_model_id": self.env["ir.model"]._get_id(record._name),
                "res_id": record.id,
                "activity_type_id": activity_type.id if activity_type else False,
                "summary": summary,
                "note": note or "",
                "user_id": user_id,
            })
            log.write({
                "state": "sent",
                "sent_on": fields.Datetime.now(),
            })
        except Exception as e:
            log.write({
                "state": "failed",
                "message": str(e),
            })

        return log

    @api.model
    def _cron_placeholder_notification_scan(self):
        """Placeholder cron method for scheduled notification scans.

        This method is intentionally minimal. It searches for season registrations
        in draft state older than 7 days and logs a reminder notice.

        Future modules can extend this or add their own cron methods.
        """
        Log = self.env["federation.notification.log"]
        Registration = self.env.get("federation.season.registration")

        if not Registration:
            Log.create({
                "name": "Cron: Notification Scan",
                "notification_type": "other",
                "state": "sent",
                "sent_on": fields.Datetime.now(),
                "message": "No federation.season.registration model found. No action configured.",
            })
            return

        # Search for draft registrations older than 7 days
        from datetime import timedelta
        cutoff_date = fields.Datetime.now() - timedelta(days=7)
        old_drafts = Registration.search([
            ("state", "=", "draft"),
            ("create_date", "<", cutoff_date),
        ], limit=20)

        if old_drafts:
            for reg in old_drafts:
                Log.create({
                    "name": f"Draft registration reminder: {reg.name or reg.id}",
                    "target_model": "federation.season.registration",
                    "target_res_id": reg.id,
                    "notification_type": "other",
                    "state": "sent",
                    "sent_on": fields.Datetime.now(),
                    "message": f"Season registration '{reg.name}' has been in draft state for more than 7 days.",
                })
        else:
            Log.create({
                "name": "Cron: Notification Scan",
                "notification_type": "other",
                "state": "sent",
                "sent_on": fields.Datetime.now(),
                "message": "No draft registrations older than 7 days found.",
            })