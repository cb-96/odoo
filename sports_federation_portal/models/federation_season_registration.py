from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FederationSeasonRegistration(models.Model):
    """Extend season registration with portal workflow states.

    Adds a ``submitted`` state so portal-created registrations go through
    a review cycle before federation staff confirms them.
    """

    _inherit = "federation.season.registration"

    # Override state to add submitted state
    state = fields.Selection(
        selection_add=[
            ("submitted", "Submitted"),
        ],
        ondelete={"submitted": "set default"},
    )

    user_id = fields.Many2one(
        "res.users",
        string="Submitted By",
        default=lambda self: self.env.user,
        readonly=True,
        copy=False,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Contact",
        related="user_id.partner_id",
        store=True,
        readonly=True,
    )
    rejection_reason = fields.Text(
        string="Rejection Reason",
        readonly=True,
        tracking=True,
    )

    @api.constrains("team_id", "club_id", "user_id")
    def _check_portal_ownership(self):
        """Validate portal ownership."""
        for rec in self:
            if rec.user_id and rec.team_id and rec.club_id:
                rep = self.env["federation.club.representative"].search(
                    [
                        ("user_id", "=", rec.user_id.id),
                        ("club_id", "=", rec.club_id.id),
                    ],
                    limit=1,
                )
                if not rep and not rec.user_id.has_group(
                    "sports_federation_base.group_federation_manager"
                ):
                    raise ValidationError(
                        "You can only register teams that belong to your club."
                    )

    # ------------------------------------------------------------------
    # Portal actions
    # ------------------------------------------------------------------

    def action_submit(self):
        """Submit a draft registration for review."""
        for rec in self:
            if rec.state != "draft":
                raise ValidationError("Only draft registrations can be submitted.")
            rec.state = "submitted"

    def action_reject(self, reason=None):
        """Reject a submitted registration."""
        for rec in self:
            if rec.state != "submitted":
                raise ValidationError("Only submitted registrations can be rejected.")
            rec.state = "draft"
            if reason:
                rec.rejection_reason = reason

    def action_confirm(self):
        """Confirm a submitted or draft registration."""
        invalid_registrations = self.filtered(
            lambda rec: rec.state not in ("draft", "submitted")
        )
        if invalid_registrations:
            raise ValidationError(
                "Only draft or submitted registrations can be confirmed."
            )
        return super().action_confirm()