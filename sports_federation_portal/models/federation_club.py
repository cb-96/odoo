from odoo import fields, models


class FederationClub(models.Model):
    """Extend federation.club with portal representative link."""

    _inherit = "federation.club"

    representative_ids = fields.One2many(
        "federation.club.representative",
        "club_id",
        string="Portal Representatives",
    )
    representative_count = fields.Integer(
        string="Representative Count",
        compute="_compute_representative_count",
        store=True,
    )

    def _compute_representative_count(self):
        for rec in self:
            rec.representative_count = len(rec.representative_ids)