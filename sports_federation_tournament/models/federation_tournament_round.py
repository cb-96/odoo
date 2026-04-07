from odoo import api, fields, models


class FederationTournamentRound(models.Model):
    _name = "federation.tournament.round"
    _description = "Tournament Round"
    _order = "sequence, id"

    name = fields.Char(string="Name", required=True)
    tournament_id = fields.Many2one(
        "federation.tournament",
        string="Tournament",
        related="stage_id.tournament_id",
        store=True,
    )
    stage_id = fields.Many2one(
        "federation.tournament.stage",
        string="Stage",
        required=True,
        ondelete="cascade",
    )
    group_id = fields.Many2one(
        "federation.tournament.group",
        string="Group",
        ondelete="set null",
    )
    sequence = fields.Integer(string="Sequence", default=10)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("scheduled", "Scheduled"),
            ("completed", "Completed"),
        ],
        string="Status",
        default="draft",
        required=True,
    )
    match_ids = fields.One2many("federation.match", "round_id", string="Matches")
    match_count = fields.Integer(
        string="Match Count", compute="_compute_match_count", store=True
    )

    @api.depends("match_ids")
    def _compute_match_count(self):
        for rec in self:
            rec.match_count = len(rec.match_ids)

    def action_schedule(self):
        for rec in self:
            rec.state = "scheduled"

    def action_complete(self):
        for rec in self:
            rec.state = "completed"
