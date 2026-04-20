from odoo import api, fields, models


class FederationSeason(models.Model):
    _inherit = "federation.season"

    tournament_ids = fields.One2many(
        "federation.tournament",
        "season_id",
        string="Tournaments",
    )
    tournament_count = fields.Integer(
        string="Tournaments",
        compute="_compute_tournament_count",
    )

    @api.depends("tournament_ids")
    def _compute_tournament_count(self):
        """Compute tournament count."""
        for record in self:
            record.tournament_count = len(record.tournament_ids)

    def action_view_tournaments(self):
        """Open the related tournaments."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Tournaments",
            "res_model": "federation.tournament",
            "view_mode": "list,form",
            "domain": [("season_id", "=", self.id)],
        }
