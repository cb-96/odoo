from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FederationTournamentStage(models.Model):
    _name = "federation.tournament.stage"
    _description = "Tournament Stage"
    _order = "sequence, id"

    name = fields.Char(string="Stage Name", required=True)
    tournament_id = fields.Many2one(
        "federation.tournament", string="Tournament", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(string="Sequence", default=10)
    stage_type = fields.Selection(
        [
            ("group", "Group Phase"),
            ("knockout", "Knockout"),
            ("final", "Final"),
            ("placement", "Placement"),
        ],
        string="Stage Type",
        default="group",
        required=True,
    )
    date_start = fields.Date(string="Start Date")
    date_end = fields.Date(string="End Date")
    notes = fields.Text(string="Notes")

    group_ids = fields.One2many("federation.tournament.group", "stage_id", string="Groups")
    match_ids = fields.One2many("federation.match", "stage_id", string="Matches")

    group_count = fields.Integer(string="Group Count", compute="_compute_counts", store=True)
    match_count = fields.Integer(string="Match Count", compute="_compute_counts", store=True)

    @api.depends("group_ids", "match_ids")
    def _compute_counts(self):
        for rec in self:
            rec.group_count = len(rec.group_ids)
            rec.match_count = len(rec.match_ids)

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for rec in self:
            if rec.date_end and rec.date_start and rec.date_end < rec.date_start:
                raise ValidationError("End date must be on or after start date.")