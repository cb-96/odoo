from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FederationMatchReferee(models.Model):
    _name = "federation.match.referee"
    _description = "Match Referee Assignment"
    _order = "match_id, role"

    match_id = fields.Many2one(
        "federation.match", string="Match", required=True, ondelete="cascade"
    )
    referee_id = fields.Many2one(
        "federation.referee", string="Referee", required=True, ondelete="restrict"
    )
    tournament_id = fields.Many2one(
        "federation.tournament", string="Tournament", related="match_id.tournament_id", store=True
    )
    role = fields.Selection(
        [
            ("head", "Head Referee"),
            ("assistant_1", "Assistant Referee 1"),
            ("assistant_2", "Assistant Referee 2"),
            ("fourth", "Fourth Official"),
            ("table", "Table Official"),
        ],
        string="Role",
        required=True,
        default="head",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
    )
    notes = fields.Text(string="Notes")

    _match_referee_role_unique = models.Constraint('unique (match_id, referee_id, role)', 'A referee can only be assigned once per role per match.')

    def action_confirm(self):
        for rec in self:
            rec.state = "confirmed"

    def action_done(self):
        for rec in self:
            rec.state = "done"

    def action_cancel(self):
        for rec in self:
            rec.state = "cancelled"

    def action_draft(self):
        for rec in self:
            rec.state = "draft"


class FederationMatchRefereeExtension(models.Model):
    _inherit = "federation.match"

    referee_assignment_ids = fields.One2many(
        "federation.match.referee", "match_id", string="Referee Assignments"
    )

