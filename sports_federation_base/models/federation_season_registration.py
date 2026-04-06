from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FederationSeasonRegistration(models.Model):
    _name = "federation.season.registration"
    _description = "Season Registration"
    _inherit = ["mail.thread"]
    _order = "create_date desc"

    name = fields.Char(string="Reference", readonly=True, copy=False, default="New")
    season_id = fields.Many2one(
        "federation.season", string="Season", required=True, tracking=True, ondelete="cascade"
    )
    team_id = fields.Many2one(
        "federation.team", string="Team", required=True, tracking=True, ondelete="cascade"
    )
    club_id = fields.Many2one(
        "federation.club", string="Club", related="team_id.club_id", store=True, readonly=True
    )
    division = fields.Char(string="Division / Competition")
    registration_date = fields.Date(
        string="Registration Date", default=fields.Date.context_today, required=True
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        tracking=True,
        required=True,
    )
    notes = fields.Text(string="Notes")

    _constraints = [
        models.Constraint('unique (team_id, season_id)', 'A team can only register once per season.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        if isinstance(vals_list, dict):
            vals_list = [vals_list]

        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "federation.season.registration"
                ) or "New"
        return super().create(vals_list)

    def action_confirm(self):
        for rec in self:
            rec.state = "confirmed"

    def action_cancel(self):
        for rec in self:
            rec.state = "cancelled"

    def action_draft(self):
        for rec in self:
            rec.state = "draft"