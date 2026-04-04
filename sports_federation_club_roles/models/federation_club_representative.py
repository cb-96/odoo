from odoo import api, fields, models, _


class FederationClubRepresentative(models.Model):
    """Club representative with role-based contact management.

    This model extends the basic club representative concept with:
    - Configurable role types
    - Start/end dates for representative tenure
    - Primary contact flags per role type
    - Notes for additional context
    - Portal ownership anchor for secure access

    Multiple representatives can be assigned to a club, each with different
    role types. The is_primary flag allows marking the primary contact for
    each role type category.
    """

    _name = "federation.club.representative"
    _description = "Club Representative"
    _rec_name = "display_name"
    _order = "club_id, is_primary desc, role_type_id, partner_id"

    # Core relationships
    club_id = fields.Many2one(
        "federation.club",
        string="Club",
        required=True,
        ondelete="cascade",
        index=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Contact",
        required=True,
        ondelete="cascade",
        index=True,
        help="The partner record representing this person.",
    )
    user_id = fields.Many2one(
        "res.users",
        string="Linked User",
        ondelete="set null",
        help="Optional linked portal user. This is the primary portal ownership anchor.",
    )

    # Role configuration
    role_type_id = fields.Many2one(
        "federation.club.role.type",
        string="Role Type",
        required=True,
        ondelete="restrict",
        index=True,
    )
    is_primary = fields.Boolean(
        string="Primary Contact",
        default=False,
        help="If checked, this representative is the primary contact for this role type.",
    )

    # Temporal fields
    date_start = fields.Date(
        string="Start Date",
        help="Date when this representative assumed the role.",
    )
    date_end = fields.Date(
        string="End Date",
        help="Date when this representative's role ended.",
    )

    # Status and metadata
    active = fields.Boolean(default=True)
    notes = fields.Text(string="Notes")

    # Computed fields
    display_name = fields.Char(
        compute="_compute_display_name",
        store=True,
    )
    is_current = fields.Boolean(
        string="Currently Active",
        compute="_compute_is_current",
        store=True,
        help="True if the representative's tenure is currently active.",
    )

    _sql_constraints = [
        (
            "partner_club_role_unique",
            "UNIQUE(partner_id, club_id, role_type_id)",
            "A partner can only have one representative record per club and role type.",
        ),
        (
            "user_club_role_unique",
            "UNIQUE(user_id, club_id, role_type_id)",
            "A user can only have one representative record per club and role type.",
        ),
    ]

    @api.depends("partner_id", "club_id", "role_type_id", "is_primary")
    def _compute_display_name(self):
        for rec in self:
            parts = []
            if rec.partner_id:
                parts.append(rec.partner_id.name)
            if rec.club_id:
                parts.append(rec.club_id.name)
            if rec.role_type_id:
                parts.append(rec.role_type_id.name)
            if rec.is_primary:
                parts.append("(Primary)")
            rec.display_name = " - ".join(parts) if parts else "New"

    @api.depends("date_start", "date_end", "active")
    def _compute_is_current(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if not rec.active:
                rec.is_current = False
            elif rec.date_start and rec.date_start > today:
                rec.is_current = False
            elif rec.date_end and rec.date_end < today:
                rec.is_current = False
            else:
                rec.is_current = True

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_start > rec.date_end:
                raise models.ValidationError(
                    "Start date cannot be after end date."
                )

    @api.constrains("is_primary", "club_id", "role_type_id")
    def _check_primary_uniqueness(self):
        """Ensure only one primary representative per club and role type."""
        for rec in self:
            if rec.is_primary:
                domain = [
                    ("club_id", "=", rec.club_id.id),
                    ("role_type_id", "=", rec.role_type_id.id),
                    ("is_primary", "=", True),
                    ("id", "!=", rec.id),
                ]
                existing = self.search(domain, limit=1)
                if existing:
                    raise models.ValidationError(
                        f"There is already a primary representative for "
                        f"'{rec.role_type_id.name}' at club '{rec.club_id.name}'."
                    )

    def action_view_partner(self):
        self.ensure_one()
        return {
            "name": _("Contact"),
            "type": "ir.actions.act_window",
            "res_model": "res.partner",
            "res_id": self.partner_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_user(self):
        self.ensure_one()
        return {
            "name": _("User"),
            "type": "ir.actions.act_window",
            "res_model": "res.users",
            "res_id": self.user_id.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model
    def _get_club_for_user(self, user=None):
        """Return the first active club for the given user (or current user).

        This is the primary helper used by controllers to resolve portal ownership.
        """
        user = user or self.env.user
        rep = self.search([
            ("user_id", "=", user.id),
            ("is_current", "=", True),
        ], limit=1)
        return rep.club_id if rep else self.env["federation.club"]

    @api.model
    def _get_clubs_for_user(self, user=None):
        """Return all active clubs the given user represents."""
        user = user or self.env.user
        reps = self.search([
            ("user_id", "=", user.id),
            ("is_current", "=", True),
        ])
        return reps.mapped("club_id")

    @api.model
    def _get_primary_contact(self, club, role_type_code=None):
        """Return the primary contact for a club and optional role type code."""
        domain = [
            ("club_id", "=", club.id),
            ("is_primary", "=", True),
            ("is_current", "=", True),
        ]
        if role_type_code:
            role_type = self.env["federation.club.role.type"].get_by_code(
                role_type_code
            )
            if role_type:
                domain.append(("role_type_id", "=", role_type.id))
        return self.search(domain, limit=1)

    @api.model
    def _get_portal_ownership_domain(self, user=None):
        """Return domain for records owned by the given user via representative link.

        This is a reusable helper for building portal record rules.
        """
        user = user or self.env.user
        return [("id", "in", user.representative_ids.mapped("club_id").ids)]