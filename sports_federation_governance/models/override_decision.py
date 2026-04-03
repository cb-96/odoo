from odoo import fields, models


class FederationOverrideDecision(models.Model):
    _name = "federation.override.decision"
    _description = "Federation Override Decision"
    _order = "decided_on desc, id"

    DECISION_SELECTION = [
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    request_id = fields.Many2one(
        "federation.override.request",
        string="Request",
        required=True,
        ondelete="cascade",
    )
    decision = fields.Selection(
        selection=DECISION_SELECTION,
        string="Decision",
        required=True,
    )
    decided_by_id = fields.Many2one(
        "res.users",
        string="Decided By",
        default=lambda self: self.env.user,
        required=True,
    )
    decided_on = fields.Datetime(
        string="Decided On",
        default=fields.Datetime.now,
        required=True,
    )
    note = fields.Text(string="Note")