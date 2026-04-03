from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FederationMatchResultControl(models.Model):
    _inherit = "federation.match"

    RESULT_STATE_SELECTION = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("verified", "Verified"),
        ("approved", "Approved"),
        ("contested", "Contested"),
        ("corrected", "Corrected"),
    ]

    result_state = fields.Selection(
        selection=RESULT_STATE_SELECTION,
        string="Result State",
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )
    result_submitted_by_id = fields.Many2one(
        "res.users",
        string="Submitted By",
        readonly=True,
    )
    result_submitted_on = fields.Datetime(
        string="Submitted On",
        readonly=True,
    )
    result_verified_by_id = fields.Many2one(
        "res.users",
        string="Verified By",
        readonly=True,
    )
    result_verified_on = fields.Datetime(
        string="Verified On",
        readonly=True,
    )
    result_approved_by_id = fields.Many2one(
        "res.users",
        string="Approved By",
        readonly=True,
    )
    result_approved_on = fields.Datetime(
        string="Approved On",
        readonly=True,
    )
    result_contest_reason = fields.Text(
        string="Contest Reason",
    )
    result_correction_reason = fields.Text(
        string="Correction Reason",
    )
    include_in_official_standings = fields.Boolean(
        string="Include in Official Standings",
        default=False,
        tracking=True,
    )

    def action_submit_result(self):
        """Submit the match result for verification."""
        for rec in self:
            if rec.result_state != "draft":
                raise ValidationError(
                    "Only draft results can be submitted."
                )
            rec.write({
                "result_state": "submitted",
                "result_submitted_by_id": self.env.user.id,
                "result_submitted_on": fields.Datetime.now(),
            })

    def action_verify_result(self):
        """Verify the submitted result."""
        for rec in self:
            if rec.result_state != "submitted":
                raise ValidationError(
                    "Only submitted results can be verified."
                )
            rec.write({
                "result_state": "verified",
                "result_verified_by_id": self.env.user.id,
                "result_verified_on": fields.Datetime.now(),
            })

    def action_approve_result(self):
        """Approve the verified result and include in official standings."""
        for rec in self:
            if rec.result_state != "verified":
                raise ValidationError(
                    "Only verified results can be approved."
                )
            rec.write({
                "result_state": "approved",
                "result_approved_by_id": self.env.user.id,
                "result_approved_on": fields.Datetime.now(),
                "include_in_official_standings": True,
            })

    def action_contest_result(self):
        """Contest a result (from submitted, verified, or approved)."""
        for rec in self:
            if rec.result_state not in ("submitted", "verified", "approved"):
                raise ValidationError(
                    "Only submitted, verified, or approved results can be contested."
                )
            if not rec.result_contest_reason:
                raise ValidationError(
                    "A contest reason is required."
                )
            rec.write({
                "result_state": "contested",
                "include_in_official_standings": False,
            })

    def action_correct_result(self):
        """Correct a contested or approved result."""
        for rec in self:
            if rec.result_state not in ("contested", "approved"):
                raise ValidationError(
                    "Only contested or approved results can be corrected."
                )
            if not rec.result_correction_reason:
                raise ValidationError(
                    "A correction reason is required."
                )
            rec.write({
                "result_state": "corrected",
                "include_in_official_standings": False,
            })

    def action_reset_result_to_draft(self):
        """Reset the result to draft (approvers only)."""
        for rec in self:
            rec.write({
                "result_state": "draft",
                "include_in_official_standings": False,
            })