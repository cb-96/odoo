from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FederationTeamRoster(models.Model):
    _name = "federation.team.roster"
    _description = "Team Roster"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    team_id = fields.Many2one(
        "federation.team",
        string="Team",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
    )
    season_id = fields.Many2one(
        "federation.season",
        string="Season",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    season_registration_id = fields.Many2one(
        "federation.season.registration",
        string="Season Registration",
        ondelete="set null",
        index=True,
    )
    competition_id = fields.Many2one(
        "federation.competition",
        string="Competition",
        ondelete="set null",
        index=True,
    )
    rule_set_id = fields.Many2one(
        "federation.rule.set",
        string="Rule Set",
        ondelete="set null",
    )
    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("closed", "Closed"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    valid_from = fields.Date(string="Valid From")
    valid_to = fields.Date(string="Valid To")
    line_ids = fields.One2many(
        "federation.team.roster.line",
        "roster_id",
        string="Roster Lines",
    )
    line_count = fields.Integer(
        compute="_compute_line_count",
        string="Line Count",
    )
    notes = fields.Text(string="Notes")
    club_id = fields.Many2one(
        "federation.club",
        string="Club",
        related="team_id.club_id",
        store=True,
    )
    min_players_required = fields.Integer(string="Min Players Required")
    max_players_allowed = fields.Integer(string="Max Players Allowed")

    _unique_team_season_competition_name = models.Constraint(
        'UNIQUE(team_id, season_id, competition_id, name)',
        'A roster with this name already exists for this team, season, and competition.',
    )

    @api.depends("line_ids")
    def _compute_line_count(self):
        for record in self:
            record.line_count = len(record.line_ids)

    @api.constrains("valid_from", "valid_to")
    def _check_valid_dates(self):
        for record in self:
            if record.valid_from and record.valid_to:
                if record.valid_to < record.valid_from:
                    raise ValidationError(
                        _("Valid To date cannot be before Valid From date.")
                    )

    @api.constrains("season_registration_id", "team_id", "season_id")
    def _check_season_registration_consistency(self):
        for record in self:
            if record.season_registration_id:
                if record.season_registration_id.team_id != record.team_id:
                    raise ValidationError(
                        _("Season registration must belong to the same team.")
                    )
                if record.season_registration_id.season_id != record.season_id:
                    raise ValidationError(
                        _("Season registration must belong to the same season.")
                    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("rule_set_id") and vals.get("competition_id"):
                competition = self.env["federation.competition"].browse(
                    vals["competition_id"]
                )
                if competition.rule_set_id:
                    vals["rule_set_id"] = competition.rule_set_id.id
        return super().create(vals_list)

    def write(self, vals):
        if not vals.get("rule_set_id") and vals.get("competition_id"):
            competition = self.env["federation.competition"].browse(
                vals["competition_id"]
            )
            if competition.rule_set_id:
                vals["rule_set_id"] = competition.rule_set_id.id
        return super().write(vals)

    def action_view_lines(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Roster Lines"),
            "res_model": "federation.team.roster.line",
            "view_mode": "list,form",
            "domain": [("roster_id", "=", self.id)],
            "context": {"default_roster_id": self.id},
        }

    def action_set_draft(self):
        self.write({"status": "draft"})

    def action_activate(self):
        self.write({"status": "active"})

    def action_close(self):
        self.write({"status": "closed"})


class FederationTeamRosterLine(models.Model):
    _name = "federation.team.roster.line"
    _description = "Team Roster Line"

    roster_id = fields.Many2one(
        "federation.team.roster",
        string="Roster",
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
    status = fields.Selection(
        [
            ("active", "Active"),
            ("inactive", "Inactive"),
            ("suspended", "Suspended"),
            ("removed", "Removed"),
        ],
        default="active",
        required=True,
    )
    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To")
    jersey_number = fields.Char(string="Jersey Number")
    is_captain = fields.Boolean(string="Is Captain", default=False)
    is_vice_captain = fields.Boolean(string="Is Vice Captain", default=False)
    notes = fields.Text(string="Notes")
    license_id = fields.Many2one(
        "federation.player.license",
        string="License",
        ondelete="set null",
    )
    eligible = fields.Boolean(
        compute="_compute_eligible",
        string="Eligible",
        store=False,
    )
    team_id = fields.Many2one(
        "federation.team",
        string="Team",
        related="roster_id.team_id",
        store=True,
    )
    season_id = fields.Many2one(
        "federation.season",
        string="Season",
        related="roster_id.season_id",
        store=True,
    )
    competition_id = fields.Many2one(
        "federation.competition",
        string="Competition",
        related="roster_id.competition_id",
        store=True,
    )

    _unique_roster_player_date_from = models.Constraint(
        'UNIQUE(roster_id, player_id, date_from)',
        'A roster line for this player with this start date already exists.',
    )

    @api.depends("status", "license_id", "license_id.expiry_date")
    def _compute_eligible(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.status != "active":
                record.eligible = False
            elif record.license_id and record.license_id.expiry_date:
                record.eligible = record.license_id.expiry_date >= today
            else:
                record.eligible = True

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for record in self:
            if record.date_from and record.date_to:
                if record.date_to < record.date_from:
                    raise ValidationError(
                        _("Date To cannot be before Date From.")
                    )

    @api.constrains("is_captain", "roster_id", "status")
    def _check_single_captain(self):
        for record in self:
            if record.is_captain and record.status == "active":
                domain = [
                    ("roster_id", "=", record.roster_id.id),
                    ("is_captain", "=", True),
                    ("status", "=", "active"),
                    ("id", "!=", record.id),
                ]
                if self.search_count(domain) > 0:
                    raise ValidationError(
                        _("Only one active captain is allowed per roster.")
                    )

    @api.constrains("is_vice_captain", "roster_id", "status")
    def _check_single_vice_captain(self):
        for record in self:
            if record.is_vice_captain and record.status == "active":
                domain = [
                    ("roster_id", "=", record.roster_id.id),
                    ("is_vice_captain", "=", True),
                    ("status", "=", "active"),
                    ("id", "!=", record.id),
                ]
                if self.search_count(domain) > 0:
                    raise ValidationError(
                        _("Only one active vice captain is allowed per roster.")
                    )