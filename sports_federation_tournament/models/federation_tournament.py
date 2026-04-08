from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FederationTournament(models.Model):
    _name = "federation.tournament"
    _description = "Federation Tournament"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_start desc, name"

    name = fields.Char(string="Tournament Name", required=True, tracking=True)
    code = fields.Char(string="Code", copy=False)
    active = fields.Boolean(default=True)
    date_start = fields.Date(string="Start Date", required=True, tracking=True)
    date_end = fields.Date(string="End Date", tracking=True)
    location = fields.Char(string="Location")
    season_id = fields.Many2one("federation.season", string="Season", tracking=True)
    tournament_type = fields.Selection(
        [
            ("single_day", "Single Day"),
            ("multi_day", "Multi Day"),
        ],
        string="Type",
        default="single_day",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("open", "Open"),
            ("in_progress", "In Progress"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )
    max_participants = fields.Integer(string="Max Participants", tracking=True)
    edition_id = fields.Many2one(
        "federation.competition.edition",
        string="Competition Edition",
        tracking=True,
        ondelete="set null",
        help="The competition edition (season-specific) this division/tournament belongs to.",
    )
    competition_id = fields.Many2one(
        "federation.competition",
        string="Competition",
        tracking=True,
        ondelete="set null",
    )
    rule_set_id = fields.Many2one(
        "federation.rule.set",
        string="Rule Set",
        tracking=True,
        ondelete="set null",
        help="Competition rules to apply. If set on the linked competition, that rule set is used by default.",
    )
    notes = fields.Text(string="Notes")

    stage_ids = fields.One2many("federation.tournament.stage", "tournament_id", string="Stages")
    participant_ids = fields.One2many(
        "federation.tournament.participant", "tournament_id", string="Participants"
    )
    match_ids = fields.One2many("federation.match", "tournament_id", string="Matches")

    stage_count = fields.Integer(string="Stage Count", compute="_compute_counts", store=True)
    participant_count = fields.Integer(
        string="Participant Count", compute="_compute_counts", store=True
    )
    match_count = fields.Integer(string="Match Count", compute="_compute_counts", store=True)

    _code_unique = models.Constraint('unique (code)', 'Tournament code must be unique.')

    @api.depends("stage_ids", "participant_ids", "match_ids")
    def _compute_counts(self):
        for rec in self:
            rec.stage_count = len(rec.stage_ids)
            rec.participant_count = len(rec.participant_ids)
            rec.match_count = len(rec.match_ids)

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for rec in self:
            if rec.date_end and rec.date_start and rec.date_end < rec.date_start:
                raise ValidationError("End date must be on or after start date.")

    @api.onchange("edition_id")
    def _onchange_edition_id(self):
        if self.edition_id:
            self.season_id = self.edition_id.season_id
            self.competition_id = self.edition_id.competition_id
            if self.edition_id.rule_set_id and not self.rule_set_id:
                self.rule_set_id = self.edition_id.rule_set_id

    def action_open(self):
        for rec in self:
            rec.state = "open"

    def action_start(self):
        for rec in self:
            rec.state = "in_progress"

    def action_close(self):
        for rec in self:
            rec.state = "closed"

    def action_cancel(self):
        for rec in self:
            rec.state = "cancelled"

    def action_draft(self):
        for rec in self:
            rec.state = "draft"

    def action_view_stages(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('sports_federation_tournament.federation_tournament_stage_action')
        action['domain'] = [('tournament_id', '=', self.id)]
        return action

    def action_view_participants(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('sports_federation_tournament.federation_tournament_participant_action')
        action['domain'] = [('tournament_id', '=', self.id)]
        return action

    def action_view_matches(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('sports_federation_tournament.federation_match_action')
        action['domain'] = [('tournament_id', '=', self.id)]
        return action