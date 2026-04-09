from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FederationSeason(models.Model):
    _name = "federation.season"
    _description = "Federation Season"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_start desc"

    name = fields.Char(string="Season Name", required=True, tracking=True)
    code = fields.Char(string="Code", copy=False)
    active = fields.Boolean(default=True)
    date_start = fields.Date(string="Start Date", required=True, tracking=True)
    date_end = fields.Date(string="End Date", required=True, tracking=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("open", "Open"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        tracking=True,
        required=True,
    )
    notes = fields.Text(string="Notes")

    registration_ids = fields.One2many(
        "federation.season.registration", "season_id", string="Registrations"
    )
    registration_count = fields.Integer(
        string="Registration Count", compute="_compute_registration_count", store=True
    )

    _code_unique = models.Constraint('unique (code)', 'Season code must be unique.')

    @api.depends("registration_ids")
    def _compute_registration_count(self):
        for rec in self:
            rec.registration_count = len(rec.registration_ids)

    def action_view_registrations(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('sports_federation_base.federation_season_registration_action')
        action['domain'] = [('season_id', '=', self.id)]
        return action

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_start >= rec.date_end:
                raise ValidationError("End date must be after start date.")

    def action_open(self):
        for rec in self:
            rec.state = "open"

    def action_close(self):
        for rec in self:
            rec.state = "closed"

    def action_cancel(self):
        for rec in self:
            rec.state = "cancelled"

    def action_draft(self):
        for rec in self:
            rec.state = "draft"