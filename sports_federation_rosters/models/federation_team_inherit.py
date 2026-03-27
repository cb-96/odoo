from odoo import fields, models


class FederationTeam(models.Model):
    _inherit = "federation.team"

    roster_ids = fields.One2many(
        "federation.team.roster",
        "team_id",
        string="Rosters",
    )
    roster_count = fields.Integer(
        compute="_compute_roster_count",
        string="Roster Count",
    )

    def _compute_roster_count(self):
        for record in self:
            record.roster_count = len(record.roster_ids)