from odoo import api, fields, models


class FederationClubRepresentative(models.Model):
    """Links portal users (res.users / res.partner) to federation clubs.

    A portal user who is a representative of a club can view and manage
    that club's teams, season registrations, and tournament registrations
    through the portal.
    """

    _name = "federation.club.representative"
    _description = "Club Representative"
    _rec_name = "display_name"
    _order = "club_id, user_id"

    club_id = fields.Many2one(
        "federation.club",
        string="Club",
        required=True,
        ondelete="cascade",
    )
    user_id = fields.Many2one(
        "res.users",
        string="Portal User",
        required=True,
        ondelete="cascade",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Contact",
        related="user_id.partner_id",
        store=True,
        readonly=True,
    )
    role = fields.Selection(
        [
            ("primary", "Primary Representative"),
            ("secondary", "Secondary Representative"),
        ],
        string="Role",
        default="primary",
        required=True,
    )
    active = fields.Boolean(default=True)
    display_name = fields.Char(compute="_compute_display_name", store=True)

    _sql_constraints = [
        (
            "user_club_unique",
            "UNIQUE(user_id, club_id)",
            "A user can only be a representative of a club once.",
        ),
    ]

    @api.depends("user_id", "club_id", "role")
    def _compute_display_name(self):
        for rec in self:
            if rec.user_id and rec.club_id:
                rec.display_name = (
                    f"{rec.user_id.name} - {rec.club_id.name} ({rec.role})"
                )
            else:
                rec.display_name = "New"

    @api.model
    def _get_club_for_user(self, user=None):
        """Return the first active club for the given user (or current user).

        This is the primary helper used by controllers to resolve
        ownership.
        """
        user = user or self.env.user
        rep = self.search([("user_id", "=", user.id)], limit=1)
        return rep.club_id if rep else self.env["federation.club"]

    @api.model
    def _get_clubs_for_user(self, user=None):
        """Return all active clubs the given user represents."""
        user = user or self.env.user
        reps = self.search([("user_id", "=", user.id)])
        return reps.mapped("club_id")