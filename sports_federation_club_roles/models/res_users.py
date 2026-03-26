from odoo import api, fields, models


class ResUsers(models.Model):
    """Extend res.users with club representative links for portal ownership."""

    _inherit = "res.users"

    representative_ids = fields.One2many(
        "federation.club.representative",
        "user_id",
        string="Club Representative Roles",
        help="Club representative records linked to this user for portal access.",
    )
    representative_count = fields.Integer(
        string="Representative Role Count",
        compute="_compute_representative_count",
        store=True,
    )
    represented_club_ids = fields.Many2many(
        "federation.club",
        string="Represented Clubs",
        compute="_compute_represented_club_ids",
        store=True,
        help="Clubs this user represents (via representative records).",
    )

    @api.depends("representative_ids")
    def _compute_representative_count(self):
        for rec in self:
            rec.representative_count = len(rec.representative_ids)

    @api.depends("representative_ids.club_id")
    def _compute_represented_club_ids(self):
        for rec in self:
            rec.represented_club_ids = rec.representative_ids.mapped("club_id")

    def action_view_federation_representatives(self):
        """Open the representative roles list for this user."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Club Representative Roles",
            "res_model": "federation.club.representative",
            "view_mode": "tree,form",
            "domain": [("user_id", "=", self.id)],
            "context": {"default_user_id": self.id},
        }