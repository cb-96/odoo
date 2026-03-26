import logging
import math
import random
from odoo import models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class KnockoutService(models.AbstractModel):
    _name = "federation.knockout.service"
    _description = "Knockout Bracket Generation Service"

    def generate(self, tournament, stage, participants, options):
        """
        Generate knockout bracket matches.

        Args:
            tournament: federation.tournament record
            stage: federation.tournament.stage record
            participants: list of federation.tournament.participant records
            options: dict with keys:
                - seeding: str (seed, random, manual)
                - bracket_size: str (natural, power_of_two)
                - start_datetime: datetime or False
                - interval_hours: int
                - venue: str or False
                - overwrite: bool

        Returns:
            list of created federation.match records
        """
        self._validate_inputs(tournament, stage, participants, options)

        if not options.get("overwrite"):
            self._check_existing_matches(stage)

        teams = self._apply_seeding(participants, options.get("seeding", "seed"))
        bracket_size = self._determine_bracket_size(len(teams), options.get("bracket_size", "natural"))
        teams, bye_teams = self._handle_byes(teams, bracket_size)
        matches = self._create_first_round(tournament, stage, teams, options)

        _logger.info(
            "Generated %d knockout matches for tournament %s, stage %s (bracket size %d)",
            len(matches), tournament.name, stage.name, bracket_size
        )
        return matches

    def _validate_inputs(self, tournament, stage, participants, options):
        if tournament.state not in ("open", "in_progress"):
            raise UserError(_("Tournament must be Open or In Progress."))
        if len(participants) < 2:
            raise UserError(_("At least 2 participants required."))

    def _check_existing_matches(self, stage):
        existing = self.env["federation.match"].search([("stage_id", "=", stage.id)])
        if existing:
            raise UserError(_("Existing matches found. Enable overwrite to replace."))

    def _apply_seeding(self, participants, seeding):
        if seeding == "random":
            teams = [p.team_id for p in participants]
            random.shuffle(teams)
            return teams
        elif seeding == "seed":
            sorted_p = sorted(participants, key=lambda p: p.seed or 999)
            return [p.team_id for p in sorted_p]
        else:
            return [p.team_id for p in participants]

    def _determine_bracket_size(self, count, mode):
        if mode == "power_of_two":
            return 2 ** math.ceil(math.log2(count))
        return count

    def _handle_byes(self, teams, bracket_size):
        if len(teams) >= bracket_size:
            return teams[:bracket_size], []
        bye_count = bracket_size - len(teams)
        bye_teams = teams[-bye_count:] if bye_count > 0 else []
        return teams, bye_teams

    def _create_first_round(self, tournament, stage, teams, options):
        Match = self.env["federation.match"]
        matches = []
        n = len(teams)
        half = n // 2
        start_dt = options.get("start_datetime")
        interval = options.get("interval_hours", 0)
        venue = options.get("venue", "")

        for i in range(half):
            home = teams[i]
            away = teams[n - 1 - i]
            vals = {
                "tournament_id": tournament.id,
                "stage_id": stage.id,
                "home_team_id": home.id,
                "away_team_id": away.id,
                "state": "draft",
                "venue": venue or "",
            }
            if start_dt:
                from datetime import timedelta
                vals["date_scheduled"] = start_dt + timedelta(hours=i * interval)
            matches.append(Match.create(vals))
        return matches