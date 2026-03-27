from odoo import fields, models


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