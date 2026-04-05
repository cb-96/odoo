from odoo import _, fields, models


class FederationMatch(models.Model):
    _inherit = "federation.match"

    match_sheet_ids = fields.One2many(
        "federation.match.sheet",
        "match_id",
        string="Match Sheets",
    )
    match_sheet_count = fields.Integer(
        compute="_compute_match_sheet_count",
        string="Match Sheet Count",
    )

    def _compute_match_sheet_count(self):
        for record in self:
            record.match_sheet_count = len(record.match_sheet_ids)

    def action_view_match_sheets(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "sports_federation_rosters.action_federation_match_sheet"
        )
        action["domain"] = [("match_id", "=", self.id)]
        action["context"] = {"default_match_id": self.id}
        return action