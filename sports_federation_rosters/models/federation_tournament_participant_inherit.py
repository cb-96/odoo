from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FederationTournamentParticipant(models.Model):
    _inherit = "federation.tournament.participant"

    ready_for_confirmation = fields.Boolean(
        compute="_compute_confirmation_readiness",
        string="Roster Deadline Satisfied",
    )
    roster_deadline_date = fields.Date(
        compute="_compute_confirmation_readiness",
        string="Roster Deadline",
    )
    readiness_roster_id = fields.Many2one(
        "federation.team.roster",
        compute="_compute_confirmation_readiness",
        string="Team Roster",
    )
    confirmation_feedback = fields.Text(
        compute="_compute_confirmation_readiness",
        string="Roster Feedback",
    )

    @api.depends(
        "team_id",
        "tournament_id",
        "tournament_id.season_id",
        "tournament_id.date_start",
        "tournament_id.competition_id",
        "tournament_id.match_ids.date_scheduled",
        "tournament_id.match_ids.home_team_id",
        "tournament_id.match_ids.away_team_id",
        "state",
    )
    def _compute_confirmation_readiness(self):
        for record in self:
            assessment = record._get_roster_assessment()
            record.ready_for_confirmation = not bool(assessment["blocking_issues"])
            record.roster_deadline_date = assessment["deadline_date"] or False
            record.readiness_roster_id = assessment["roster"].id if assessment["roster"] else False
            record.confirmation_feedback = assessment["feedback"]

    def _get_readiness_roster(self):
        self.ensure_one()
        if not self.team_id or not self.tournament_id:
            return self.env["federation.team.roster"]
        return self.team_id._get_tournament_roster_assessment(self.tournament_id)[
            "roster"
        ]

    def _get_roster_assessment(self, today=None):
        self.ensure_one()
        if not self.team_id or not self.tournament_id:
            return {
                "roster": self.env["federation.team.roster"],
                "first_match_date": False,
                "deadline_date": False,
                "deadline_reached": False,
                "blocking_issues": [],
                "feedback": False,
            }
        return self.team_id._get_tournament_roster_assessment(
            self.tournament_id,
            today=today,
        )

    def action_confirm(self):
        for record in self:
            assessment = record._get_roster_assessment()
            if assessment["blocking_issues"]:
                raise ValidationError(
                    _(
                        "Participant '%(participant)s' cannot be confirmed because the roster deadline has been reached:\n- %(issues)s"
                    )
                    % {
                        "participant": record.display_name,
                        "issues": "\n- ".join(assessment["blocking_issues"]),
                    }
                )
        return super().action_confirm()