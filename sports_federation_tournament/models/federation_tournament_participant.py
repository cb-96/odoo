from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FederationTournamentParticipant(models.Model):
    _name = "federation.tournament.participant"
    _description = "Tournament Participant"
    _order = "name"

    name = fields.Char(string="Name", compute="_compute_name", store=True)
    tournament_id = fields.Many2one(
        "federation.tournament", string="Tournament", required=True, ondelete="cascade"
    )
    team_id = fields.Many2one(
        "federation.team", string="Team", required=True, ondelete="restrict"
    )
    club_id = fields.Many2one(
        "federation.club", string="Club", related="team_id.club_id", store=True, readonly=True
    )
    stage_id = fields.Many2one(
        "federation.tournament.stage", string="Stage", ondelete="set null"
    )
    group_id = fields.Many2one(
        "federation.tournament.group", string="Group", ondelete="set null"
    )
    seed = fields.Integer(string="Seed")
    registration_date = fields.Date(
        string="Registration Date", default=fields.Date.context_today
    )
    state = fields.Selection(
        [
            ("registered", "Registered"),
            ("confirmed", "Confirmed"),
            ("withdrawn", "Withdrawn"),
        ],
        string="Status",
        default="registered",
        required=True,
    )
    notes = fields.Text(string="Notes")

    _sql_constraints = [
        (
            "team_tournament_unique",
            "UNIQUE(team_id, tournament_id)",
            "A team can only participate once per tournament.",
        ),
    ]

    @api.depends("team_id", "tournament_id")
    def _compute_name(self):
        for rec in self:
            if rec.team_id and rec.tournament_id:
                rec.name = f"{rec.team_id.name} @ {rec.tournament_id.name}"
            else:
                rec.name = "New"

    def action_confirm(self):
        for rec in self:
            rec.state = "confirmed"

    def action_withdraw(self):
        for rec in self:
            rec.state = "withdrawn"