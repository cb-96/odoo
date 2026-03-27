from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FederationSuspension(models.Model):
    _name = "federation.suspension"
    _description = "Suspension"
    _order = "date_start desc, id desc"

    name = fields.Char(required=True)
    case_id = fields.Many2one(
        "federation.disciplinary.case",
        string="Case",
        required=True,
        ondelete="cascade",
        index=True,
    )
    player_id = fields.Many2one(
        "federation.player",
        string="Player",
        required=True,
        ondelete="restrict",
        index=True,
    )
    date_start = fields.Date(string="Start Date", required=True)
    date_end = fields.Date(string="End Date", required=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("expired", "Expired"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
    )
    notes = fields.Text(string="Notes")

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for record in self:
            if record.date_end and record.date_start:
                if record.date_end < record.date_start:
                    raise ValidationError(
                        "End date must be on or after start date."
                    )

    def action_activate(self):
        for record in self:
            record.state = "active"

    def action_cancel(self):
        for record in self:
            record.state = "cancelled"