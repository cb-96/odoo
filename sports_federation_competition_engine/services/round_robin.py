import logging
import itertools
from odoo import models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class RoundRobinService(models.AbstractModel):
    _name = "federation.round.robin.service"
    _description = "Round Robin Schedule Generation Service"

    def generate(self, tournament, stage, participants, options):
        """
        Generate round-robin match schedule.

        Args:
            tournament: federation.tournament record
            stage: federation.tournament.stage record
            participants: list of federation.tournament.participant records
            options: dict with keys:
                - double_round: bool
                - start_datetime: datetime or False
                - interval_hours: int
                - venue: str or False
                - overwrite: bool
                - group: federation.tournament.group or False

        Returns:
            list of created federation.match records
        """
        self._validate_inputs(tournament, stage, participants, options)

        if not options.get("overwrite"):
            self._check_existing_matches(stage, options.get("group"))

        teams = [p.team_id for p in participants]
        pairings = self._generate_pairings(teams, options.get("double_round", False))
        matches = self._create_matches(tournament, stage, pairings, options)

        _logger.info(
            "Generated %d round-robin matches for tournament %s, stage %s",
            len(matches), tournament.name, stage.name
        )
        return matches

    def _validate_inputs(self, tournament, stage, participants, options):
        if tournament.state not in ("open", "in_progress"):
            raise UserError(_("Tournament must be Open or In Progress to generate matches."))
        if len(participants) < 2:
            raise UserError(_("At least 2 participants are required for round-robin."))

    def _check_existing_matches(self, stage, group):
        domain = [("stage_id", "=", stage.id)]
        if group:
            domain.append(("group_id", "=", group.id))
        existing = self.env["federation.match"].search(domain)
        if existing:
            raise UserError(_(
                "Existing matches found in this stage/group. "
                "Enable overwrite mode to replace them."
            ))

    def _generate_pairings(self, teams, double_round):
        """
        Generate round-robin pairings using the circle method.

        The algorithm fixes the first team and rotates the rest.
        For odd participant counts, a bye (False) is added.
        Home/away alternates by round to ensure fairness.
        """
        n = len(teams)
        has_bye = n % 2 == 1
        if has_bye:
            teams = list(teams) + [False]
            n += 1

        rounds = n - 1
        half = n // 2
        working = list(teams)
        all_pairings = []

        for round_num in range(rounds):
            for i in range(half):
                home = working[i]
                away = working[n - 1 - i]
                if home and away:
                    # Alternate home/away by round for fairness
                    if round_num % 2 == 0:
                        all_pairings.append((home, away))
                    else:
                        all_pairings.append((away, home))
            # Rotate: keep first fixed, rotate rest clockwise
            working = [working[0]] + [working[-1]] + working[1:-1]

        if double_round:
            reversed_pairings = [(away, home) for home, away in all_pairings]
            all_pairings.extend(reversed_pairings)

        return all_pairings

    def _create_matches(self, tournament, stage, pairings, options):
        Match = self.env["federation.match"]
        matches = []
        start_dt = options.get("start_datetime")
        interval = options.get("interval_hours", 0)
        venue = options.get("venue", "")
        group = options.get("group")

        for idx, (home, away) in enumerate(pairings):
            vals = {
                "tournament_id": tournament.id,
                "stage_id": stage.id,
                "home_team_id": home.id,
                "away_team_id": away.id,
                "state": "draft",
                "venue": venue or "",
            }
            if group:
                vals["group_id"] = group.id
            if start_dt:
                from datetime import timedelta
                vals["date_scheduled"] = start_dt + timedelta(hours=idx * interval)
            matches.append(Match.create(vals))

        return matches