from odoo import _, fields, models


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

    def action_view_rosters(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "sports_federation_rosters.action_federation_team_roster"
        )
        action["domain"] = [("team_id", "=", self.id)]
        action["context"] = {"default_team_id": self.id}
        return action