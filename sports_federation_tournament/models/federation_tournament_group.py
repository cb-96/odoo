from odoo import api, fields, models


class FederationTournamentGroup(models.Model):
    _name = "federation.tournament.group"
    _description = "Tournament Group / Poule"
    _order = "sequence, id"

    name = fields.Char(string="Group Name", required=True)
    stage_id = fields.Many2one(
        "federation.tournament.stage", string="Stage", required=True, ondelete="cascade"
    )
    tournament_id = fields.Many2one(
        "federation.tournament", string="Tournament", related="stage_id.tournament_id", store=True
    )
    sequence = fields.Integer(string="Sequence", default=10)
    max_participants = fields.Integer(string="Max Participants")
    notes = fields.Text(string="Notes")

    participant_ids = fields.One2many(
        "federation.tournament.participant", "group_id", string="Participants"
    )
    match_ids = fields.One2many("federation.match", "group_id", string="Matches")

    participant_count = fields.Integer(
        string="Participant Count", compute="_compute_counts", store=True
    )
    match_count = fields.Integer(string="Match Count", compute="_compute_counts", store=True)

    @api.depends("participant_ids", "match_ids")
    def _compute_counts(self):
        for rec in self:
            rec.participant_count = len(rec.participant_ids)
            rec.match_count = len(rec.match_ids)