from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


def _dedupe_reasons(reasons):
    """Handle dedupe reasons."""
    unique_reasons = []
    seen = set()
    for reason in reasons:
        if reason and reason not in seen:
            unique_reasons.append(reason)
            seen.add(reason)
    return unique_reasons


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
    match_kickoff = fields.Datetime(
        related="match_id.date_scheduled",
        string="Match Kickoff",
        store=True,
        index=True,
        readonly=True,
    )
    match_scheduled_date = fields.Date(
        related="match_id.scheduled_date",
        string="Match Date",
        store=True,
        index=True,
        readonly=True,
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
    ready_for_submission = fields.Boolean(
        compute="_compute_readiness",
        string="Ready For Submission",
        store=True,
    )
    readiness_feedback = fields.Text(
        compute="_compute_readiness",
        string="Readiness Feedback",
        store=True,
    )
    substitution_count = fields.Integer(
        compute="_compute_substitution_count",
        string="Substitution Count",
    )
    locked_on = fields.Datetime(string="Locked On", readonly=True)
    locked_by_id = fields.Many2one(
        "res.users",
        string="Locked By",
        readonly=True,
    )
    audit_event_ids = fields.One2many(
        "federation.participation.audit",
        "match_sheet_id",
        string="Audit Events",
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
        """Compute line count."""
        for record in self:
            record.line_count = len(record.line_ids)

    @api.depends("line_ids.entered_minute")
    def _compute_substitution_count(self):
        """Compute substitution count."""
        for record in self:
            record.substitution_count = len(
                record.line_ids.filtered(lambda line: bool(line.entered_minute))
            )

    @api.model_create_multi
    def create(self, vals_list):
        """Create records with module-specific defaults and side effects."""
        records = super().create(vals_list)
        for record in records:
            record._log_audit_event(
                "match_sheet_created",
                _(
                    "Match sheet '%(sheet)s' created for match '%(match)s'."
                )
                % {
                    "sheet": record.display_name,
                    "match": record.match_id.display_name,
                },
            )
        return records

    def write(self, vals):
        """Update records with module-specific side effects."""
        if not self.env.context.get("bypass_match_sheet_lock"):
            locked_records = self.filtered(lambda rec: rec.state == "locked")
            if locked_records:
                raise ValidationError(
                    _("Locked match sheets cannot be modified.")
                )
            approved_records = self.filtered(lambda rec: rec.state == "approved")
            allowed_on_approved = {"state", "notes", "locked_on", "locked_by_id"}
            if approved_records and any(field not in allowed_on_approved for field in vals):
                raise ValidationError(
                    _(
                        "Approved match sheets cannot change their declared squad. Record substitutions on the sheet lines instead."
                    )
                )
        return super().write(vals)

    @api.depends(
        "roster_id",
        "roster_id.status",
        "roster_id.readiness_feedback",
        "line_ids",
        "line_ids.player_id",
        "line_ids.roster_line_id",
        "line_ids.eligible",
        "line_ids.eligibility_feedback",
        "match_id",
        "match_id.date_scheduled",
    )
    def _compute_readiness(self):
        """Compute readiness."""
        for record in self:
            issues = record._get_submission_issues()
            record.ready_for_submission = not bool(issues)
            record.readiness_feedback = "\n".join(issues) if issues else False

    @api.constrains("side", "team_id", "match_id")
    def _check_side_team_consistency(self):
        """Validate side team consistency."""
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

    def _get_effective_rule_set(self):
        """Return effective rule set."""
        self.ensure_one()
        if self.roster_id:
            return self.roster_id._get_effective_rule_set()
        service = self.env.get("federation.eligibility.service")
        if service is not None:
            return service._resolve_rule_set(self.match_id)
        return self.env["federation.rule.set"]

    def _get_reference_date(self):
        """Return reference date."""
        self.ensure_one()
        if self.match_id.date_scheduled:
            return fields.Datetime.to_datetime(self.match_id.date_scheduled).date()
        return fields.Date.context_today(self)

    def _get_submission_issues(self):
        """Return submission issues."""
        self.ensure_one()
        issues = []

        if not self.roster_id:
            issues.append(_("Select an active roster before submitting the match sheet."))
        elif self.roster_id.status != "active":
            issues.append(_("The selected roster must be active before submission."))

        if not self.line_ids:
            issues.append(_("Add at least one match-sheet line before submission."))

        eligible_line_count = 0
        for line in self.line_ids:
            reasons = line._get_eligibility_reasons()
            if reasons:
                issues.append(
                    _("Player '%(player)s': %(reasons)s")
                    % {
                        "player": line.player_id.display_name,
                        "reasons": "; ".join(reasons),
                    }
                )
            else:
                eligible_line_count += 1

        if self.roster_id:
            min_required, max_allowed = self.roster_id._get_required_player_bounds()
        else:
            rule_set = self._get_effective_rule_set()
            min_required = rule_set.squad_min_size if rule_set else 0
            max_allowed = rule_set.squad_max_size if rule_set else 0

        if min_required and eligible_line_count < min_required:
            issues.append(
                _(
                    "Eligible submitted players (%(actual)s) are below the required minimum of %(expected)s."
                )
                % {"actual": eligible_line_count, "expected": min_required}
            )
        if max_allowed and len(self.line_ids) > max_allowed:
            issues.append(
                _(
                    "Submitted players (%(actual)s) exceed the allowed maximum of %(expected)s."
                )
                % {"actual": len(self.line_ids), "expected": max_allowed}
            )

        return issues

    def _log_audit_event(self, event_type, description, player=False):
        """Handle log audit event."""
        Audit = self.env.get("federation.participation.audit")
        if Audit is None:
            return False
        for record in self:
            Audit.create_event(
                event_type=event_type,
                description=description,
                team=record.team_id,
                roster=record.roster_id,
                match_sheet=record,
                match=record.match_id,
                player=player,
            )
        return True

    def action_submit(self):
        """Execute the submit action."""
        for record in self:
            issues = record._get_submission_issues()
            if issues:
                raise ValidationError(
                    _("Match sheet '%(sheet)s' is not ready for submission:\n- %(issues)s")
                    % {
                        "sheet": record.display_name,
                        "issues": "\n- ".join(issues),
                    }
                )
        self.write({"state": "submitted"})
        for record in self:
            record._log_audit_event(
                "match_sheet_submitted",
                _("Match sheet '%(sheet)s' submitted.")
                % {"sheet": record.display_name},
            )

    def action_reset_to_draft(self):
        """Reset a submitted match sheet back to draft for corrections."""
        for record in self:
            if record.state != "submitted":
                raise ValidationError(
                    _("Only submitted match sheets can be reset to draft.")
                )
        self.write({"state": "draft"})
        for record in self:
            record._log_audit_event(
                "match_sheet_reset",
                _("Match sheet '%(sheet)s' reset to draft.")
                % {"sheet": record.display_name},
            )

    def action_approve(self):
        """Execute the approve action."""
        for record in self:
            if record.state != "submitted":
                raise ValidationError(
                    _("Only submitted match sheets can be approved.")
                )
        self.write({"state": "approved"})
        for record in self:
            record._log_audit_event(
                "match_sheet_approved",
                _("Match sheet '%(sheet)s' approved.")
                % {"sheet": record.display_name},
            )

    def action_lock(self):
        """Execute the lock action."""
        for record in self:
            if record.state != "approved":
                raise ValidationError(
                    _("Only approved match sheets can be locked.")
                )
        self.write(
            {
                "state": "locked",
                "locked_on": fields.Datetime.now(),
                "locked_by_id": self.env.user.id,
            }
        )
        for record in self:
            record._log_audit_event(
                "match_sheet_locked",
                _("Match sheet '%(sheet)s' locked.")
                % {"sheet": record.display_name},
            )


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
    entered_minute = fields.Integer(string="Entered Minute")
    left_minute = fields.Integer(string="Left Minute")
    notes = fields.Text(string="Notes")
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

    _unique_match_sheet_player = models.Constraint(
        'UNIQUE(match_sheet_id, player_id)',
        'A player cannot appear twice on the same match sheet.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Create records with module-specific defaults and side effects."""
        self._assert_parent_sheets_allow_new_lines(vals_list)
        records = super().create(vals_list)
        for record in records:
            record.match_sheet_id._log_audit_event(
                "sheet_line_added",
                _("Player '%(player)s' added to the match sheet.")
                % {"player": record.player_id.display_name},
                player=record.player_id,
            )
        return records

    def write(self, vals):
        """Update records with module-specific side effects."""
        self._assert_parent_sheet_line_editable(vals)
        result = super().write(vals)
        if {"entered_minute", "left_minute"} & set(vals):
            for record in self:
                minute_bits = []
                if record.entered_minute:
                    minute_bits.append(
                        _("entered in minute %(minute)s")
                        % {"minute": record.entered_minute}
                    )
                if record.left_minute:
                    minute_bits.append(
                        _("left in minute %(minute)s")
                        % {"minute": record.left_minute}
                    )
                record.match_sheet_id._log_audit_event(
                    "substitution_recorded",
                    _("Substitution updated for '%(player)s': %(details)s.")
                    % {
                        "player": record.player_id.display_name,
                        "details": ", ".join(minute_bits) or _("no minute recorded"),
                    },
                    player=record.player_id,
                )
        else:
            tracked_fields = {
                "player_id",
                "roster_line_id",
                "is_starter",
                "is_substitute",
                "is_captain",
                "jersey_number",
                "notes",
            }
            changed_fields = sorted(tracked_fields.intersection(vals))
            if changed_fields:
                field_labels = ", ".join(self._fields[field].string for field in changed_fields)
                for record in self:
                    record.match_sheet_id._log_audit_event(
                        "sheet_line_updated",
                        _("Match-sheet line for '%(player)s' updated: %(fields)s.")
                        % {
                            "player": record.player_id.display_name,
                            "fields": field_labels,
                        },
                        player=record.player_id,
                    )
        return result

    def unlink(self):
        """Delete records after applying module-specific safeguards."""
        self._assert_parent_sheet_line_editable()
        audit_payloads = [
            (
                record.match_sheet_id,
                record.player_id,
                _("Player '%(player)s' removed from the match sheet.")
                % {"player": record.player_id.display_name},
            )
            for record in self
        ]
        result = super().unlink()
        for sheet, player, description in audit_payloads:
            sheet._log_audit_event(
                "sheet_line_removed",
                description,
                player=player,
            )
        return result

    @api.depends(
        "player_id",
        "roster_line_id",
        "roster_line_id.eligible",
        "roster_line_id.eligibility_feedback",
        "roster_line_id.status",
        "roster_line_id.date_from",
        "roster_line_id.date_to",
        "match_sheet_id",
        "match_sheet_id.roster_id",
        "match_sheet_id.team_id",
        "match_sheet_id.match_id",
        "match_sheet_id.match_id.date_scheduled",
        "match_sheet_id.match_id.tournament_id",
    )
    def _compute_eligible(self):
        """Compute eligible."""
        for record in self:
            reasons = record._get_eligibility_reasons()
            record.eligible = not bool(reasons)
            record.eligibility_feedback = "\n".join(reasons) if reasons else False

    def _assert_parent_sheets_allow_new_lines(self, vals_list):
        """Handle assert parent sheets allow new lines."""
        sheet_ids = [vals.get("match_sheet_id") for vals in vals_list if vals.get("match_sheet_id")]
        sheets = self.env["federation.match.sheet"].browse(sheet_ids)
        for sheet in sheets:
            if sheet.state in ("approved", "locked"):
                raise ValidationError(
                    _(
                        "Cannot add players to match sheet '%(sheet)s' once it is approved or locked."
                    )
                    % {"sheet": sheet.display_name}
                )

    def _assert_parent_sheet_line_editable(self, vals=None):
        """Handle assert parent sheet line editable."""
        for record in self:
            if record.match_sheet_id.state == "locked":
                raise ValidationError(
                    _("Locked match sheets cannot be modified.")
                )
            if record.match_sheet_id.state == "approved":
                allowed_fields = {"entered_minute", "left_minute", "notes"}
                if vals is None or any(field not in allowed_fields for field in vals):
                    raise ValidationError(
                        _(
                            "Approved match sheets cannot change player selection or lineup roles. Record substitutions instead."
                        )
                    )

    @api.constrains("is_starter", "is_substitute")
    def _check_starter_substitute(self):
        """Validate starter substitute."""
        for record in self:
            if record.is_starter and record.is_substitute:
                raise ValidationError(
                    _("A player cannot be both a starter and a substitute.")
                )

    @api.constrains("entered_minute", "left_minute", "is_starter", "is_substitute")
    def _check_substitution_governance(self):
        """Validate substitution governance."""
        for record in self:
            entered_minute = record.entered_minute or False
            left_minute = record.left_minute or False

            if entered_minute:
                if entered_minute <= 0:
                    raise ValidationError(
                        _("Entered minute must be a positive number.")
                    )
                if not record.is_substitute:
                    raise ValidationError(
                        _("Only substitute lines can record an entered minute.")
                    )
            if left_minute:
                if left_minute <= 0:
                    raise ValidationError(
                        _("Left minute must be a positive number.")
                    )
                if not (record.is_starter or entered_minute):
                    raise ValidationError(
                        _(
                            "Only starters or players who entered from the bench can record a left minute."
                        )
                    )
            if entered_minute and left_minute:
                if left_minute <= entered_minute:
                    raise ValidationError(
                        _("A player cannot leave before or at the same minute they entered.")
                    )

    @api.constrains("roster_line_id", "match_sheet_id")
    def _check_roster_line_consistency(self):
        """Validate roster line consistency."""
        for record in self:
            if record.roster_line_id and record.match_sheet_id.roster_id:
                if record.roster_line_id.roster_id != record.match_sheet_id.roster_id:
                    raise ValidationError(
                        _("Roster line must belong to the match sheet's roster.")
                    )

    def _get_eligibility_reasons(self):
        """Return eligibility reasons."""
        self.ensure_one()
        if not self.player_id or not self.match_sheet_id:
            return []

        sheet = self.match_sheet_id
        reference_date = sheet._get_reference_date()
        reasons = []

        if sheet.roster_id and not self.roster_line_id:
            reasons.append(_("Select a roster line from the chosen roster."))

        if self.roster_line_id:
            if self.roster_line_id.player_id != self.player_id:
                reasons.append(_("Selected roster line does not belong to the chosen player."))
            if self.roster_line_id.status != "active":
                reasons.append(_("Selected roster line is not active."))
            if self.roster_line_id.date_from and reference_date < self.roster_line_id.date_from:
                reasons.append(
                    _("Selected roster line is not active before %(date)s.")
                    % {"date": self.roster_line_id.date_from}
                )
            if self.roster_line_id.date_to and reference_date > self.roster_line_id.date_to:
                reasons.append(
                    _("Selected roster line expired after %(date)s.")
                    % {"date": self.roster_line_id.date_to}
                )
            if self.roster_line_id.team_id and self.roster_line_id.team_id != sheet.team_id:
                reasons.append(_("Selected roster line belongs to a different team."))
            if self.roster_line_id.eligibility_feedback:
                reasons.extend(self.roster_line_id.eligibility_feedback.splitlines())

        service = self.env.get("federation.eligibility.service")
        rule_set = sheet._get_effective_rule_set()
        if service is not None and rule_set:
            context = {
                "match_date": reference_date,
                "tournament_id": sheet.match_id.tournament_id.id if sheet.match_id.tournament_id else None,
                "season_id": sheet.match_id.tournament_id.season_id.id if sheet.match_id.tournament_id and sheet.match_id.tournament_id.season_id else None,
                "team_id": sheet.team_id.id if sheet.team_id else None,
                "club_id": sheet.team_id.club_id.id if sheet.team_id and sheet.team_id.club_id else None,
            }
            if self.roster_line_id and self.roster_line_id.license_id:
                context["license_id"] = self.roster_line_id.license_id.id
            result = service.check_player_eligibility(self.player_id, rule_set, context=context)
            reasons.extend(result.get("reasons", []))

        return _dedupe_reasons(reasons)