from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FederationCompetition(models.Model):
    _name = "federation.competition"
    _description = "Federation Competition"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, name"

    name = fields.Char(string="Competition Name", required=True, tracking=True)
    code = fields.Char(string="Code", copy=False, tracking=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(string="Sequence", default=10)
    description = fields.Text(string="Description")
    competition_type = fields.Selection(
        [
            ("league", "League"),
            ("cup", "Cup / Knockout"),
            ("tournament", "Tournament"),
            ("friendly", "Friendly"),
            ("other", "Other"),
        ],
        string="Competition Type",
        default="league",
        required=True,
        tracking=True,
    )
    season_id = fields.Many2one(
        "federation.season", string="Season", tracking=True, ondelete="set null"
    )
    rule_set_id = fields.Many2one(
        "federation.rule.set",
        string="Rule Set",
        tracking=True,
        ondelete="set null",
        help="Default rule set applied to tournaments or registrations referencing this competition.",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("closed", "Closed"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )
    tournament_ids = fields.One2many(
        "federation.tournament", "competition_id", string="Tournaments"
    )
    tournament_count = fields.Integer(
        string="Tournament Count", compute="_compute_tournament_count", store=False
    )
    notes = fields.Text(string="Notes")

    _code_unique = models.Constraint('unique (code)', 'Competition code must be unique.')

    @api.depends("tournament_ids")
    def _compute_tournament_count(self):
        for rec in self:
            rec.tournament_count = len(rec.tournament_ids)

    def action_activate(self):
        for rec in self:
            rec.state = "active"

    def action_close(self):
        for rec in self:
            rec.state = "closed"

    def action_draft(self):
        for rec in self:
            rec.state = "draft"

    def action_view_tournaments(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('sports_federation_tournament.federation_tournament_action')
        action['domain'] = [('competition_id', '=', self.id)]
        return action