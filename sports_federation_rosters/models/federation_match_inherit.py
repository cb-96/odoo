from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class FederationMatch(models.Model):
    _inherit = "federation.match"

    match_sheet_ids = fields.One2many(
        "federation.match.sheet",
        "match_id",
        string="Match Sheets",
    )
    match_sheet_count = fields.Integer(
        compute="_compute_match_sheet_count",
        string="Match Sheet Count",
    )

    def _compute_match_sheet_count(self):
        for record in self:
            record.match_sheet_count = len(record.match_sheet_ids)

    def action_view_match_sheets(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "sports_federation_rosters.action_federation_match_sheet"
        )
        action["domain"] = [("match_id", "=", self.id)]
        action["context"] = {"default_match_id": self.id}
        return action

    def _get_team_roster_deadline_issues(self):
        self.ensure_one()
        if (
            not self.tournament_id
            or not self.date_scheduled
            or not (self.home_team_id or self.away_team_id)
        ):
            return []

        scheduled_date = fields.Datetime.to_datetime(self.date_scheduled).date()
        today = fields.Date.context_today(self)
        if scheduled_date < today:
            return []

        issues = []
        for team in (self.home_team_id | self.away_team_id):
            assessment = team._get_tournament_roster_assessment(
                self.tournament_id,
                today=today,
            )
            if assessment["blocking_issues"]:
                issues.append(
                    _("Team '%(team)s': %(issues)s")
                    % {
                        "team": team.display_name,
                        "issues": "; ".join(assessment["blocking_issues"]),
                    }
                )
        return issues

    @api.constrains(
        "tournament_id",
        "home_team_id",
        "away_team_id",
        "date_scheduled",
        "state",
    )
    def _check_team_roster_deadlines(self):
        for record in self:
            if record.state == "cancelled":
                continue
            issues = record._get_team_roster_deadline_issues()
            if issues:
                raise ValidationError(
                    _(
                        "Matches cannot be scheduled on or after the roster deadline without an active ready team roster:\n- %(issues)s"
                    )
                    % {"issues": "\n- ".join(issues)}
                )