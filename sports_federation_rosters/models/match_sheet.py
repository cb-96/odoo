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
    ready_for_submission = fields.Boolean(
        compute="_compute_readiness",
        string="Ready For Submission",
    )
    readiness_feedback = fields.Text(
        compute="_compute_readiness",
        string="Readiness Feedback",
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
        for record in self:
            issues = record._get_submission_issues()
            record.ready_for_submission = not bool(issues)
            record.readiness_feedback = "\n".join(issues) if issues else False

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

    def _get_effective_rule_set(self):
        self.ensure_one()
        if self.roster_id:
            return self.roster_id._get_effective_rule_set()
        service = self.env.get("federation.eligibility.service")
        if service:
            return service._resolve_rule_set(self.match_id)
        return self.env["federation.rule.set"]

    def _get_reference_date(self):
        self.ensure_one()
        if self.match_id.date_scheduled:
            return fields.Datetime.to_datetime(self.match_id.date_scheduled).date()
        return fields.Date.context_today(self)

    def _get_submission_issues(self):
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

    def action_submit(self):
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
    eligibility_feedback = fields.Text(
        compute="_compute_eligible",
        string="Eligibility Feedback",
        store=False,
    )

    _unique_match_sheet_player = models.Constraint(
        'UNIQUE(match_sheet_id, player_id)',
        'A player cannot appear twice on the same match sheet.',
    )

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
        for record in self:
            reasons = record._get_eligibility_reasons()
            record.eligible = not bool(reasons)
            record.eligibility_feedback = "\n".join(reasons) if reasons else False

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

    def _get_eligibility_reasons(self):
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
        if service and rule_set:
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