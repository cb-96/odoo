from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


def _dedupe_reasons(reasons):
    unique_reasons = []
    seen = set()
    for reason in reasons:
        if reason and reason not in seen:
            unique_reasons.append(reason)
            seen.add(reason)
    return unique_reasons


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
    ready_for_activation = fields.Boolean(
        compute="_compute_readiness",
        string="Ready For Activation",
    )
    readiness_feedback = fields.Text(
        compute="_compute_readiness",
        string="Readiness Feedback",
    )

    _unique_team_season_competition_name = models.Constraint(
        'UNIQUE(team_id, season_id, competition_id, name)',
        'A roster with this name already exists for this team, season, and competition.',
    )

    @api.depends("line_ids")
    def _compute_line_count(self):
        for record in self:
            record.line_count = len(record.line_ids)

    @api.depends(
        "status",
        "valid_from",
        "valid_to",
        "rule_set_id",
        "competition_id",
        "competition_id.rule_set_id",
        "min_players_required",
        "max_players_allowed",
        "line_ids",
        "line_ids.status",
        "line_ids.date_from",
        "line_ids.date_to",
        "line_ids.player_id",
        "line_ids.player_id.gender",
        "line_ids.player_id.state",
        "line_ids.player_id.birth_date",
        "line_ids.license_id",
        "line_ids.license_id.state",
        "line_ids.license_id.issue_date",
        "line_ids.license_id.expiry_date",
        "line_ids.license_id.season_id",
        "line_ids.license_id.club_id",
    )
    def _compute_readiness(self):
        for record in self:
            issues = record._get_readiness_issues()
            record.ready_for_activation = not bool(issues)
            record.readiness_feedback = "\n".join(issues) if issues else False

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

    def _get_effective_rule_set(self):
        self.ensure_one()
        return self.rule_set_id or (
            self.competition_id.rule_set_id
            if self.competition_id and self.competition_id.rule_set_id
            else self.env["federation.rule.set"]
        )

    def _get_reference_date(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        if self.valid_from and self.valid_from > today:
            return self.valid_from
        if self.season_id and self.season_id.date_start and self.season_id.date_start > today:
            return self.season_id.date_start
        return today

    def _get_required_player_bounds(self):
        self.ensure_one()
        rule_set = self._get_effective_rule_set()
        min_required = self.min_players_required or (rule_set.squad_min_size if rule_set else 0)
        max_allowed = self.max_players_allowed or (rule_set.squad_max_size if rule_set else 0)
        return min_required, max_allowed

    def _get_readiness_issues(self, reference_date=None):
        self.ensure_one()
        reference_date = reference_date or self._get_reference_date()
        issues = []

        if self.valid_from and reference_date < self.valid_from:
            issues.append(
                _("Roster is not valid yet on %(date)s.")
                % {"date": self.valid_from}
            )
        if self.valid_to and reference_date > self.valid_to:
            issues.append(
                _("Roster expired before %(date)s.")
                % {"date": reference_date}
            )

        active_lines = self.line_ids.filtered(lambda line: line.status == "active")
        if not active_lines:
            issues.append(_("Add at least one active roster line before activation."))

        eligible_active_count = 0
        for line in active_lines:
            reasons = line._get_eligibility_reasons(reference_date=reference_date)
            if reasons:
                issues.append(
                    _("Player '%(player)s': %(reasons)s")
                    % {
                        "player": line.player_id.display_name,
                        "reasons": "; ".join(reasons),
                    }
                )
            else:
                eligible_active_count += 1

        min_required, max_allowed = self._get_required_player_bounds()
        if min_required and eligible_active_count < min_required:
            issues.append(
                _(
                    "Eligible active players (%(actual)s) are below the required minimum of %(expected)s."
                )
                % {"actual": eligible_active_count, "expected": min_required}
            )
        if max_allowed and len(active_lines) > max_allowed:
            issues.append(
                _(
                    "Active roster lines (%(actual)s) exceed the allowed maximum of %(expected)s."
                )
                % {"actual": len(active_lines), "expected": max_allowed}
            )

        return issues

    def action_set_draft(self):
        self.write({"status": "draft"})

    def action_activate(self):
        for record in self:
            issues = record._get_readiness_issues()
            if issues:
                raise ValidationError(
                    _("Roster '%(roster)s' is not ready to activate:\n- %(issues)s")
                    % {
                        "roster": record.display_name,
                        "issues": "\n- ".join(issues),
                    }
                )
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
    eligibility_feedback = fields.Text(
        compute="_compute_eligible",
        string="Eligibility Feedback",
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

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._validate_player_eligibility()
        return records

    def write(self, vals):
        result = super().write(vals)
        self._validate_player_eligibility()
        return result

    @api.depends(
        "status",
        "date_from",
        "date_to",
        "player_id",
        "player_id.gender",
        "player_id.state",
        "player_id.birth_date",
        "license_id",
        "license_id.state",
        "license_id.issue_date",
        "license_id.expiry_date",
        "license_id.season_id",
        "license_id.club_id",
        "roster_id",
        "roster_id.team_id",
        "roster_id.team_id.gender",
        "roster_id.season_id",
        "roster_id.club_id",
        "roster_id.competition_id",
        "roster_id.rule_set_id",
    )
    def _compute_eligible(self):
        for record in self:
            reasons = record._get_eligibility_reasons()
            record.eligible = not bool(reasons)
            record.eligibility_feedback = "\n".join(reasons) if reasons else False

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

    @api.constrains("player_id", "roster_id")
    def _check_player_eligibility_rules(self):
        self._validate_player_eligibility()

    def _get_eligibility_context(self, reference_date=None):
        self.ensure_one()
        roster = self.roster_id
        context = {"match_date": reference_date or roster._get_reference_date()}
        if roster.season_id:
            context["season_id"] = roster.season_id.id
        if roster.club_id:
            context["club_id"] = roster.club_id.id
        if roster.team_id:
            context["team_id"] = roster.team_id.id
        if roster.competition_id:
            context["competition_id"] = roster.competition_id.id
        if self.license_id:
            context["license_id"] = self.license_id.id
        return context

    def _get_eligibility_reasons(self, reference_date=None):
        self.ensure_one()
        player = self.player_id
        roster = self.roster_id
        if not player or not roster:
            return []

        reference_date = reference_date or roster._get_reference_date()
        reasons = []
        team = roster.team_id

        if self.status != "active":
            reasons.append(_("Roster line is not active."))
        if self.date_from and reference_date < self.date_from:
            reasons.append(
                _("Player is not active on this roster before %(date)s.")
                % {"date": self.date_from}
            )
        if self.date_to and reference_date > self.date_to:
            reasons.append(
                _("Player is no longer active on this roster after %(date)s.")
                % {"date": self.date_to}
            )

        if team and team.gender in ("male", "female"):
            if not player.gender:
                reasons.append(
                    _(
                        "Player '%(player)s' must have a gender set to join team '%(team)s'."
                    )
                    % {"player": player.display_name, "team": team.display_name}
                )
            elif player.gender != team.gender:
                reasons.append(
                    _(
                        "Player '%(player)s' (%(player_gender)s) is not eligible for team '%(team)s' (%(team_gender)s)."
                    )
                    % {
                        "player": player.display_name,
                        "player_gender": player.gender,
                        "team": team.display_name,
                        "team_gender": team.gender,
                    }
                )

        Service = self.env.get("federation.eligibility.service")
        rule_set = roster._get_effective_rule_set()
        if Service and rule_set:
            result = Service.check_player_eligibility(
                player,
                rule_set,
                context=self._get_eligibility_context(reference_date=reference_date),
            )
            reasons.extend(result.get("reasons", []))

        return _dedupe_reasons(reasons)

    def _validate_player_eligibility(self):
        """Validate direct team compatibility and rule-set eligibility."""
        for record in self:
            reasons = record._get_eligibility_reasons()
            if not reasons:
                continue
            raise ValidationError(
                _("Player '%(player)s' is not eligible for this roster: %(reasons)s")
                % {
                    "player": record.player_id.display_name,
                    "reasons": "; ".join(reasons),
                }
            )