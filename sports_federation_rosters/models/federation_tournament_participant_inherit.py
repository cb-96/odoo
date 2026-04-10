from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FederationTournamentParticipant(models.Model):
    _inherit = "federation.tournament.participant"

    ready_for_confirmation = fields.Boolean(
        compute="_compute_confirmation_readiness",
        string="Ready For Confirmation",
    )
    readiness_roster_id = fields.Many2one(
        "federation.team.roster",
        compute="_compute_confirmation_readiness",
        string="Readiness Roster",
    )
    confirmation_feedback = fields.Text(
        compute="_compute_confirmation_readiness",
        string="Confirmation Feedback",
    )

    @api.depends(
        "team_id",
        "tournament_id",
        "tournament_id.season_id",
        "tournament_id.competition_id",
        "state",
    )
    def _compute_confirmation_readiness(self):
        for record in self:
            roster = record._get_readiness_roster()
            issues = record._get_confirmation_issues(roster=roster)
            record.ready_for_confirmation = not bool(issues)
            record.readiness_roster_id = roster.id if roster else False
            record.confirmation_feedback = "\n".join(issues) if issues else False

    def _get_readiness_roster(self):
        self.ensure_one()
        Roster = self.env["federation.team.roster"]
        if not self.team_id or not self.tournament_id.season_id:
            return Roster.browse([])

        domain = [
            ("team_id", "=", self.team_id.id),
            ("season_id", "=", self.tournament_id.season_id.id),
            ("status", "=", "active"),
        ]
        if self.tournament_id.competition_id:
            competition_specific = Roster.search(
                domain + [("competition_id", "=", self.tournament_id.competition_id.id)],
                limit=1,
                order="valid_from desc, id desc",
            )
            if competition_specific:
                return competition_specific

        return Roster.search(
            domain + [("competition_id", "=", False)],
            limit=1,
            order="valid_from desc, id desc",
        )

    def _get_confirmation_issues(self, roster=None):
        self.ensure_one()
        roster = roster if roster is not None else self._get_readiness_roster()
        if not roster:
            return [
                _(
                    "Create and activate a team roster for this team and season before confirming the participant."
                )
            ]

        reference_date = self.tournament_id.date_start or fields.Date.context_today(self)
        issues = roster._get_readiness_issues(reference_date=reference_date)
        if issues:
            return [
                _("Roster '%(roster)s' is not ready: %(issues)s")
                % {
                    "roster": roster.display_name,
                    "issues": "; ".join(issues),
                }
            ]
        return []

    def action_confirm(self):
        for record in self:
            issues = record._get_confirmation_issues()
            if issues:
                raise ValidationError(
                    _(
                        "Participant '%(participant)s' cannot be confirmed:\n- %(issues)s"
                    )
                    % {
                        "participant": record.display_name,
                        "issues": "\n- ".join(issues),
                    }
                )
        return super().action_confirm()