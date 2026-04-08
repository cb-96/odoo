from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FederationTournamentRegistration(models.Model):
    """Tournament registration request submitted by portal users.

    This model captures the portal-side registration intent. Federation
    staff reviews submissions and, upon confirmation, the system can
    optionally create a ``federation.tournament.participant`` record.

    Workflow: draft -> submitted -> confirmed / rejected / cancelled
    """

    _name = "federation.tournament.registration"
    _description = "Tournament Registration Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(
        string="Reference",
        readonly=True,
        copy=False,
        default="New",
    )
    tournament_id = fields.Many2one(
        "federation.tournament",
        string="Tournament",
        required=True,
        tracking=True,
        ondelete="cascade",
    )
    team_id = fields.Many2one(
        "federation.team",
        string="Team",
        required=True,
        tracking=True,
        ondelete="restrict",
    )
    club_id = fields.Many2one(
        "federation.club",
        string="Club",
        related="team_id.club_id",
        store=True,
        readonly=True,
    )
    season_id = fields.Many2one(
        "federation.season",
        string="Season",
        related="tournament_id.season_id",
        store=True,
        readonly=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Submitted By",
        default=lambda self: self.env.user,
        readonly=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Contact",
        related="user_id.partner_id",
        store=True,
        readonly=True,
    )
    registration_date = fields.Date(
        string="Registration Date",
        default=fields.Date.context_today,
        required=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("confirmed", "Confirmed"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )
    notes = fields.Text(string="Notes")
    rejection_reason = fields.Text(
        string="Rejection Reason",
        readonly=True,
        tracking=True,
    )
    participant_id = fields.Many2one(
        "federation.tournament.participant",
        string="Linked Participant",
        readonly=True,
        copy=False,
        ondelete="set null",
    )

    _team_tournament_unique = models.Constraint(
        'UNIQUE(team_id, tournament_id)',
        'A team can only submit one registration request per tournament.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        if isinstance(vals_list, dict):
            vals_list = [vals_list]

        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "federation.tournament.registration"
                ) or "New"
        return super().create(vals_list)

    @api.constrains("team_id", "club_id")
    def _check_portal_ownership(self):
        """Ensure that when created via portal, the team belongs to the
        submitting user's club."""
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
    # Actions
    # ------------------------------------------------------------------

    def action_submit(self):
        """Submit the registration for review."""
        for rec in self:
            if rec.state != "draft":
                raise ValidationError("Only draft registrations can be submitted.")
            rec.state = "submitted"

    def action_confirm(self):
        """Confirm the registration and optionally create a participant."""
        for rec in self:
            if rec.state != "submitted":
                raise ValidationError("Only submitted registrations can be confirmed.")
            rec.state = "confirmed"
            # Create participant record if one does not already exist
            if not rec.participant_id:
                existing = self.env["federation.tournament.participant"].search(
                    [
                        ("tournament_id", "=", rec.tournament_id.id),
                        ("team_id", "=", rec.team_id.id),
                    ],
                    limit=1,
                )
                if existing:
                    rec.participant_id = existing.id
                else:
                    participant = self.env["federation.tournament.participant"].create(
                        {
                            "tournament_id": rec.tournament_id.id,
                            "team_id": rec.team_id.id,
                            "registration_date": rec.registration_date,
                            "state": "registered",
                        }
                    )
                    rec.participant_id = participant.id

    def action_reject(self, reason=None):
        """Reject the registration with an optional reason."""
        for rec in self:
            if rec.state != "submitted":
                raise ValidationError("Only submitted registrations can be rejected.")
            rec.state = "rejected"
            if reason:
                rec.rejection_reason = reason

    def action_cancel(self):
        """Cancel the registration (portal or backend)."""
        for rec in self:
            if rec.state in ("confirmed",):
                raise ValidationError("Confirmed registrations cannot be cancelled.")
            rec.state = "cancelled"

    def action_reset_draft(self):
        """Reset to draft (backend only)."""
        for rec in self:
            rec.state = "draft"

    def action_view_participant(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "sports_federation_tournament.federation_tournament_participant_action"
        )
        action["res_id"] = self.participant_id.id
        action["views"] = [(False, "form")]
        return action