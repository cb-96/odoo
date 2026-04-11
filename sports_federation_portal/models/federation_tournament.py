from odoo import api, fields, models


class FederationTournament(models.Model):
    _inherit = "federation.tournament"

    registration_request_ids = fields.One2many(
        "federation.tournament.registration",
        "tournament_id",
        string="Registration Requests",
    )
    registration_request_count = fields.Integer(
        string="Registration Request Count",
        compute="_compute_registration_request_count",
    )

    @api.depends("registration_request_ids")
    def _compute_registration_request_count(self):
        for tournament in self:
            tournament.registration_request_count = len(tournament.registration_request_ids)

    def action_view_registration_requests(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "sports_federation_portal.action_federation_tournament_registration"
        )
        action["domain"] = [("tournament_id", "=", self.id)]
        action["context"] = {"default_tournament_id": self.id}
        return action