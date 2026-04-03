from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FederationOverrideRequest(models.Model):
    _name = "federation.override.request"
    _description = "Federation Override Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "requested_on desc, id"

    REQUEST_TYPE_SELECTION = [
        ("manual_seeding", "Manual Seeding"),
        ("eligibility_waiver", "Eligibility Waiver"),
        ("late_registration", "Late Registration"),
        ("result_correction", "Result Correction"),
        ("standing_adjustment", "Standing Adjustment"),
        ("admin_forfeit", "Administrative Forfeit"),
        ("other", "Other"),
    ]

    STATE_SELECTION = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("implemented", "Implemented"),
        ("closed", "Closed"),
    ]

    name = fields.Char(string="Title", required=True, tracking=True)
    request_type = fields.Selection(
        selection=REQUEST_TYPE_SELECTION,
        string="Request Type",
        required=True,
    )
    target_model = fields.Char(string="Target Model", required=True)
    target_res_id = fields.Integer(string="Target Record ID", required=True)
    requested_by_id = fields.Many2one(
        "res.users",
        string="Requested By",
        default=lambda self: self.env.user,
        required=True,
    )
    requested_on = fields.Datetime(
        string="Requested On",
        default=fields.Datetime.now,
        required=True,
    )
    state = fields.Selection(
        selection=STATE_SELECTION,
        string="State",
        default="draft",
        required=True,
        tracking=True,
    )
    reason = fields.Text(string="Reason", required=True)
    implementation_note = fields.Text(string="Implementation Note")
    decision_ids = fields.One2many(
        "federation.override.decision",
        "request_id",
        string="Decisions",
    )
    audit_note_ids = fields.One2many(
        "federation.audit.note",
        "request_id",
        string="Audit Notes",
    )

    @api.constrains("target_model")
    def _check_target_model(self):
        for record in self:
            if not record.target_model:
                raise ValidationError("Target model must not be empty.")

    @api.constrains("target_res_id")
    def _check_target_res_id(self):
        for record in self:
            if record.target_res_id <= 0:
                raise ValidationError("Target record ID must be > 0.")

    @api.constrains("reason")
    def _check_reason(self):
        for record in self:
            if not record.reason or not record.reason.strip():
                raise ValidationError("Reason is required.")

    def action_submit(self):
        """Submit the request for approval."""
        for record in self:
            if record.state != "draft":
                raise ValidationError("Only draft requests can be submitted.")
            record.state = "submitted"

    def action_approve(self):
        """Approve the request and create decision record."""
        for record in self:
            if record.state != "submitted":
                raise ValidationError("Only submitted requests can be approved.")
            record.state = "approved"
            # Create decision record
            self.env["federation.override.decision"].create({
                "request_id": record.id,
                "decision": "approved",
            })

    def action_reject(self):
        """Reject the request and create decision record."""
        for record in self:
            if record.state != "submitted":
                raise ValidationError("Only submitted requests can be rejected.")
            record.state = "rejected"
            # Create decision record
            self.env["federation.override.decision"].create({
                "request_id": record.id,
                "decision": "rejected",
            })

    def action_mark_implemented(self):
        """Mark the request as implemented."""
        for record in self:
            if record.state != "approved":
                raise ValidationError("Only approved requests can be marked as implemented.")
            record.state = "implemented"

    def action_close(self):
        """Close the request."""
        for record in self:
            if record.state not in ("implemented", "rejected"):
                raise ValidationError("Only implemented or rejected requests can be closed.")
            record.state = "closed"