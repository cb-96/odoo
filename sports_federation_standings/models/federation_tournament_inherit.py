from odoo import api, fields, models


class FederationTournament(models.Model):
    _inherit = "federation.tournament"

    standing_ids = fields.One2many(
        "federation.standing",
        "tournament_id",
        string="Standings",
    )
    standing_count = fields.Integer(
        compute="_compute_standing_count",
        string="Standing Count",
    )

    @api.depends("standing_ids")
    def _compute_standing_count(self):
        for record in self:
            record.standing_count = len(record.standing_ids)

    def action_view_standings(self):
        """Open standings for this tournament."""
        self.ensure_one()
        action = self.env.ref("sports_federation_standings.action_federation_standing").read()[0]
        action["domain"] = [("tournament_id", "=", self.id)]
        action["context"] = {"default_tournament_id": self.id}
        return action