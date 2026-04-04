from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FederationMatch(models.Model):
    _name = "federation.match"
    _description = "Federation Match"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_scheduled desc, id"

    name = fields.Char(string="Reference", compute="_compute_name", store=True)
    tournament_id = fields.Many2one(
        "federation.tournament", string="Tournament", required=True, ondelete="cascade"
    )
    stage_id = fields.Many2one(
        "federation.tournament.stage", string="Stage", ondelete="set null"
    )
    group_id = fields.Many2one(
        "federation.tournament.group", string="Group", ondelete="set null"
    )
    home_team_id = fields.Many2one(
        "federation.team", string="Home Team", ondelete="restrict"
    )
    away_team_id = fields.Many2one(
        "federation.team", string="Away Team", ondelete="restrict"
    )
    date_scheduled = fields.Datetime(string="Scheduled Date", tracking=True)
    venue = fields.Char(string="Venue")
    home_score = fields.Integer(string="Home Score", tracking=True)
    away_score = fields.Integer(string="Away Score", tracking=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("scheduled", "Scheduled"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )
    notes = fields.Text(string="Notes")

    @api.depends("home_team_id", "away_team_id")
    def _compute_name(self):
        for rec in self:
            if rec.home_team_id and rec.away_team_id:
                rec.name = f"{rec.home_team_id.name} vs {rec.away_team_id.name}"
            else:
                rec.name = "Match"

    @api.constrains("home_team_id", "away_team_id")
    def _check_teams(self):
        for rec in self:
            if rec.home_team_id and rec.away_team_id and rec.home_team_id == rec.away_team_id:
                raise ValidationError("Home and away teams cannot be the same.")

    def action_schedule(self):
        for rec in self:
            rec.state = "scheduled"

    def action_start(self):
        for rec in self:
            rec.state = "in_progress"

    def action_done(self):
        for rec in self:
            rec.state = "done"

    def action_cancel(self):
        for rec in self:
            rec.state = "cancelled"

    def action_draft(self):
        for rec in self:
            rec.state = "draft"