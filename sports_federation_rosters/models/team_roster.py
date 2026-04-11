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
        store=True,
    )
    readiness_feedback = fields.Text(
        compute="_compute_readiness",
        string="Readiness Feedback",
        store=True,
    )
    match_sheet_ids = fields.One2many(
        "federation.match.sheet",
        "roster_id",
        string="Match Sheets",
    )
    match_sheet_count = fields.Integer(
        compute="_compute_match_sheet_count",
        string="Match Sheet Count",
    )
    match_day_locked = fields.Boolean(
        compute="_compute_match_day_lock",
        string="Match-Day Locked",
    )
    match_day_lock_feedback = fields.Text(
        compute="_compute_match_day_lock",
        string="Match-Day Lock Feedback",
    )
    audit_event_ids = fields.One2many(
        "federation.participation.audit",
        "roster_id",
        string="Audit Events",
    )

    _unique_team_season_competition_name = models.Constraint(
        'UNIQUE(team_id, season_id, competition_id, name)',
        'A roster with this name already exists for this team, season, and competition.',
    )

    @api.depends("line_ids")
    def _compute_line_count(self):
        for record in self:
            record.line_count = len(record.line_ids)

    @api.depends("match_sheet_ids")
    def _compute_match_sheet_count(self):
        for record in self:
            record.match_sheet_count = len(record.match_sheet_ids)

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

    @api.depends(
        "match_sheet_ids.state",
        "match_sheet_ids.name",
        "match_sheet_ids.match_id",
        "match_sheet_ids.match_id.date_scheduled",
    )
    def _compute_match_day_lock(self):
        state_labels = dict(self.env["federation.match.sheet"]._fields["state"].selection)
        for record in self:
            locking_sheets = record._get_locking_match_sheets()
            record.match_day_locked = bool(locking_sheets)
            if locking_sheets:
                names = ", ".join(
                    "%s (%s)"
                    % (sheet.display_name, state_labels.get(sheet.state, sheet.state))
                    for sheet in locking_sheets
                )
                record.match_day_lock_feedback = _(
                    "Roster scope is locked because these match sheets already left draft: %(sheets)s."
                ) % {"sheets": names}
            else:
                record.match_day_lock_feedback = False

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
        records = super().create(vals_list)
        for record in records:
            record._log_audit_event(
                "roster_created",
                _(
                    "Roster '%(roster)s' created for team '%(team)s' in season '%(season)s'."
                )
                % {
                    "roster": record.display_name,
                    "team": record.team_id.display_name,
                    "season": record.season_id.display_name,
                },
            )
        return records

    def write(self, vals):
        self._assert_scope_editable_for_match_day(vals)
        if not vals.get("rule_set_id") and vals.get("competition_id"):
            competition = self.env["federation.competition"].browse(
                vals["competition_id"]
            )
            if competition.rule_set_id:
                vals["rule_set_id"] = competition.rule_set_id.id
        result = super().write(vals)
        tracked_fields = {
            "team_id",
            "season_id",
            "competition_id",
            "season_registration_id",
            "rule_set_id",
            "valid_from",
            "valid_to",
            "min_players_required",
            "max_players_allowed",
            "notes",
        }
        changed_fields = sorted(tracked_fields.intersection(vals))
        if changed_fields:
            field_labels = ", ".join(self._fields[field].string for field in changed_fields)
            for record in self:
                record._log_audit_event(
                    "roster_updated",
                    _("Roster updated: %(fields)s.") % {"fields": field_labels},
                )
        return result

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

    def action_view_match_sheets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Match Sheets"),
            "res_model": "federation.match.sheet",
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

    def _get_locking_match_sheets(self):
        self.ensure_one()
        return self.match_sheet_ids.filtered(
            lambda sheet: sheet.state in ("submitted", "approved", "locked")
        )

    def _log_audit_event(self, event_type, description, player=False, match_sheet=False):
        Audit = self.env.get("federation.participation.audit")
        if Audit is None:
            return False
        for record in self:
            Audit.create_event(
                event_type=event_type,
                description=description,
                team=record.team_id,
                roster=record,
                match_sheet=match_sheet,
                player=player,
            )
        return True

    def _assert_scope_editable_for_match_day(self, vals):
        if self.env.context.get("bypass_match_day_lock"):
            return
        protected_fields = {
            "team_id",
            "season_id",
            "competition_id",
            "season_registration_id",
            "rule_set_id",
            "valid_from",
            "valid_to",
            "min_players_required",
            "max_players_allowed",
        }
        changed_fields = sorted(protected_fields.intersection(vals))
        if not changed_fields:
            return
        field_labels = ", ".join(self._fields[field].string for field in changed_fields)
        for record in self:
            if record.match_day_locked:
                raise ValidationError(
                    _(
                        "Roster '%(roster)s' cannot change %(fields)s because submitted, approved, or locked match sheets already reference it."
                    )
                    % {
                        "roster": record.display_name,
                        "fields": field_labels,
                    }
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
        for record in self:
            if record.match_day_locked:
                raise ValidationError(
                    _(
                        "Roster '%(roster)s' cannot return to draft after match-day sheets have already left draft."
                    )
                    % {"roster": record.display_name}
                )
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
        for record in self:
            record._log_audit_event(
                "roster_activated",
                _("Roster '%(roster)s' activated for competition operations.")
                % {"roster": record.display_name},
            )

    def action_close(self):
        self.with_context(bypass_match_day_lock=True).write({"status": "closed"})
        for record in self:
            record._log_audit_event(
                "roster_closed",
                _("Roster '%(roster)s' closed.") % {"roster": record.display_name},
            )


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
        store=True,
    )
    eligibility_feedback = fields.Text(
        compute="_compute_eligible",
        string="Eligibility Feedback",
        store=True,
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
        for record in records:
            record.roster_id._log_audit_event(
                "roster_line_added",
                _("Player '%(player)s' added to the roster.")
                % {"player": record.player_id.display_name},
                player=record.player_id,
            )
        return records

    def write(self, vals):
        self._assert_not_locked_for_match_day(vals)
        result = super().write(vals)
        self._validate_player_eligibility()
        tracked_fields = {
            "player_id",
            "status",
            "date_from",
            "date_to",
            "jersey_number",
            "is_captain",
            "is_vice_captain",
            "license_id",
            "notes",
        }
        changed_fields = sorted(tracked_fields.intersection(vals))
        if changed_fields:
            field_labels = ", ".join(self._fields[field].string for field in changed_fields)
            for record in self:
                record.roster_id._log_audit_event(
                    "roster_line_updated",
                    _("Roster line for '%(player)s' updated: %(fields)s.")
                    % {
                        "player": record.player_id.display_name,
                        "fields": field_labels,
                    },
                    player=record.player_id,
                )
        return result

    def unlink(self):
        self._assert_not_locked_for_match_day()
        audit_payloads = [
            (
                record.roster_id,
                record.player_id,
                _("Player '%(player)s' removed from the roster.")
                % {"player": record.player_id.display_name},
            )
            for record in self
        ]
        result = super().unlink()
        for roster, player, description in audit_payloads:
            roster._log_audit_event(
                "roster_line_removed",
                description,
                player=player,
            )
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

    def _get_locking_match_sheet_lines(self):
        self.ensure_one()
        return self.env["federation.match.sheet.line"].search(
            [
                ("roster_line_id", "=", self.id),
                ("match_sheet_id.state", "in", ("submitted", "approved", "locked")),
            ]
        )

    def _assert_not_locked_for_match_day(self, vals=None):
        if self.env.context.get("bypass_match_day_lock"):
            return
        protected_fields = {
            "player_id",
            "status",
            "date_from",
            "date_to",
            "jersey_number",
            "is_captain",
            "is_vice_captain",
            "license_id",
        }
        if vals is not None and not protected_fields.intersection(vals):
            return
        for record in self:
            locking_lines = record._get_locking_match_sheet_lines()
            if locking_lines:
                sheet_names = ", ".join(locking_lines.mapped("match_sheet_id").mapped("display_name"))
                raise ValidationError(
                    _(
                        "Roster line for player '%(player)s' is locked because it already appears on live match sheet(s): %(sheets)s."
                    )
                    % {
                        "player": record.player_id.display_name,
                        "sheets": sheet_names,
                    }
                )

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
        if Service is not None and rule_set:
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