from odoo import api, fields, models


class FederationClub(models.Model):
    _name = "federation.club"
    _description = "Federation Club"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(string="Club Name", required=True, tracking=True)
    code = fields.Char(string="Code", copy=False, tracking=True)
    active = fields.Boolean(default=True)
    street = fields.Char(string="Street")
    street2 = fields.Char(string="Street 2")
    city = fields.Char(string="City")
    state_id = fields.Many2one("res.country.state", string="State")
    country_id = fields.Many2one("res.country", string="Country")
    zip = fields.Char(string="ZIP")
    email = fields.Char(string="Email", tracking=True)
    phone = fields.Char(string="Phone", tracking=True)
    mobile = fields.Char(string="Mobile")
    website = fields.Char(string="Website")
    founded_date = fields.Date(string="Founded Date")
    logo = fields.Binary(string="Logo")
    notes = fields.Text(string="Notes")

    team_ids = fields.One2many("federation.team", "club_id", string="Teams")
    team_count = fields.Integer(string="Team Count", compute="_compute_team_count", store=True)

    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "Club code must be unique."),
    ]

    @api.depends("team_ids")
    def _compute_team_count(self):
        for rec in self:
            rec.team_count = len(rec.team_ids)

    @api.constrains("email")
    def _check_email(self):
        for rec in self:
            if rec.email and "@" not in rec.email:
                raise models.ValidationError("Invalid email address.")