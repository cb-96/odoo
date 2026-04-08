from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FederationMatchSheet(models.Model):
    _name = "federation.match.sheet"
    _description = "Match Sheet"

    name = fields.Char(required=True)
    match_id = fields.Many2one(
        "federation.match",
        string="Match",
        required=True,
        ondelete="cascade",
        index=True,
    )
    team_id = fields.Many2one(
        "federation.team",
        string="Team",
        required=True,
        ondelete="restrict",
        index=True,
    )
    roster_id = fields.Many2one(
        "federation.team.roster",
        string="Roster",
        ondelete="set null",
        index=True,
    )
    side = fields.Selection(
        [
            ("home", "Home"),
            ("away", "Away"),
            ("other", "Other"),
        ],
        required=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("locked", "Locked"),
        ],
        default="draft",
        required=True,
    )
    line_ids = fields.One2many(
        "federation.match.sheet.line",
        "match_sheet_id",
        string="Sheet Lines",
    )
    line_count = fields.Integer(
        compute="_compute_line_count",
        string="Line Count",
    )
    coach_name = fields.Char(string="Coach Name")
    manager_name = fields.Char(string="Manager Name")
    notes = fields.Text(string="Notes")

    _unique_match_team_side = models.Constraint(
        'UNIQUE(match_id, team_id, side)',
        'A match sheet already exists for this team and side in this match.',
    )

    @api.depends("line_ids")
    def _compute_line_count(self):
        for record in self:
            record.line_count = len(record.line_ids)

    @api.constrains("side", "team_id", "match_id")
    def _check_side_team_consistency(self):
        for record in self:
            if record.side == "home" and record.match_id.home_team_id:
                if record.team_id != record.match_id.home_team_id:
                    raise ValidationError(
                        _("Home side team must match the match home team.")
                    )
            elif record.side == "away" and record.match_id.away_team_id:
                if record.team_id != record.match_id.away_team_id:
                    raise ValidationError(
                        _("Away side team must match the match away team.")
                    )

    def action_submit(self):
        self.write({"state": "submitted"})

    def action_approve(self):
        self.write({"state": "approved"})

    def action_lock(self):
        self.write({"state": "locked"})


class FederationMatchSheetLine(models.Model):
    _name = "federation.match.sheet.line"
    _description = "Match Sheet Line"

    match_sheet_id = fields.Many2one(
        "federation.match.sheet",
        string="Match Sheet",
        required=True,
        ondelete="cascade",
        index=True,
    )
    player_id = fields.Many2one(
        "federation.player",
        string="Player",
        required=True,
        ondelete="restrict",
        index=True,
    )
    roster_line_id = fields.Many2one(
        "federation.team.roster.line",
        string="Roster Line",
        ondelete="set null",
    )
    is_starter = fields.Boolean(string="Is Starter", default=False)
    is_substitute = fields.Boolean(string="Is Substitute", default=False)
    is_captain = fields.Boolean(string="Is Captain", default=False)
    jersey_number = fields.Char(string="Jersey Number")
    notes = fields.Text(string="Notes")
    eligible = fields.Boolean(
        compute="_compute_eligible",
        string="Eligible",
        store=False,
    )

    _unique_match_sheet_player = models.Constraint(
        'UNIQUE(match_sheet_id, player_id)',
        'A player cannot appear twice on the same match sheet.',
    )

    @api.depends("roster_line_id", "roster_line_id.eligible")
    def _compute_eligible(self):
        for record in self:
            if record.roster_line_id:
                record.eligible = record.roster_line_id.eligible
            else:
                record.eligible = True

    @api.constrains("is_starter", "is_substitute")
    def _check_starter_substitute(self):
        for record in self:
            if record.is_starter and record.is_substitute:
                raise ValidationError(
                    _("A player cannot be both a starter and a substitute.")
                )

    @api.constrains("roster_line_id", "match_sheet_id")
    def _check_roster_line_consistency(self):
        for record in self:
            if record.roster_line_id and record.match_sheet_id.roster_id:
                if record.roster_line_id.roster_id != record.match_sheet_id.roster_id:
                    raise ValidationError(
                        _("Roster line must belong to the match sheet's roster.")
                    )