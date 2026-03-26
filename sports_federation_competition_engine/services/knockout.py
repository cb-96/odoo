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
        first_round_pairs = self._build_first_round(teams, bracket_size)
        matches = self._create_matches(tournament, stage, first_round_pairs, options)

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
        """Return teams ordered by seeding method."""
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
        """Return bracket size: either natural or next power of two."""
        if mode == "power_of_two":
            return 2 ** math.ceil(math.log2(count))
        return count

    def _build_first_round(self, teams, bracket_size):
        """
        Build first round pairings with proper bye placement.

        For seeded brackets with byes:
        - Top seeds get byes (advance automatically)
        - Remaining teams are paired using standard bracket seeding:
          1 vs N, 2 vs N-1, etc.

        Returns list of (home, away) tuples for actual matches.
        Byes are not returned as matches (team advances automatically).
        """
        n_actual = len(teams)
        
        if n_actual >= bracket_size:
            # No byes needed, pair directly
            half = bracket_size // 2
            pairs = []
            for i in range(half):
                pairs.append((teams[i], teams[bracket_size - 1 - i]))
            return pairs

        # Need byes: bracket_size > n_actual
        bye_count = bracket_size - n_actual
        
        # Top seeds get byes: teams[0..bye_count-1] advance automatically
        # Remaining teams play first round
        teams_with_byes = teams[:bye_count]  # These advance, no match
        teams_playing = teams[bye_count:]     # These play first round
        
        # Number of matches in first round
        n_playing = len(teams_playing)
        half = n_playing // 2
        
        # Pair bottom teams: standard bracket seeding
        # e.g., 8 teams, 2 byes: teams_playing has 6 teams
        # Pair: seed(bye_count+1) vs seed(n_actual), seed(bye_count+2) vs seed(n_actual-1), etc.
        pairs = []
        for i in range(half):
            home = teams_playing[i]
            away = teams_playing[n_playing - 1 - i]
            pairs.append((home, away))
        
        return pairs

    def _create_matches(self, tournament, stage, pairs, options):
        """Create federation.match records for first round pairings."""
        Match = self.env["federation.match"]
        matches = []
        start_dt = options.get("start_datetime")
        interval = options.get("interval_hours", 0)
        venue = options.get("venue", "")

        for i, (home, away) in enumerate(pairs):
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
