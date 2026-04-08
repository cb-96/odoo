import logging
import math
import random
from datetime import timedelta
from odoo import models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class KnockoutService(models.AbstractModel):
    _name = "federation.knockout.service"
    _description = "Knockout Bracket Generation Service"

    def generate(self, tournament, stage, participants, options):
        """
        Generate a full knockout bracket with all rounds.

        Creates first-round matches with teams assigned, and subsequent-round
        placeholder matches linked via source_match_1_id / source_match_2_id.
        When a match result is entered, teams auto-advance through the bracket.
        """
        self._validate_inputs(tournament, stage, participants, options)

        if not options.get("overwrite"):
            self._check_existing_matches(stage)

        teams = self._apply_seeding(participants, options.get("seeding", "seed"))
        bracket_size = self._determine_bracket_size(len(teams), options.get("bracket_size", "natural"))
        first_round_pairs = self._build_first_round(teams, bracket_size)
        bracket_type = options.get("bracket_type", "winners")

        all_matches = self._create_full_bracket(
            tournament, stage, teams, bracket_size, first_round_pairs, options, bracket_type
        )

        _logger.info(
            "Generated %d knockout matches (%d rounds) for tournament %s, stage %s",
            len(all_matches),
            math.ceil(math.log2(bracket_size)) if bracket_size > 1 else 1,
            tournament.name,
            stage.name,
        )
        return all_matches

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

    def _build_first_round(self, teams, bracket_size):
        n_actual = len(teams)

        if n_actual >= bracket_size:
            half = bracket_size // 2
            pairs = []
            for i in range(half):
                pairs.append((teams[i], teams[bracket_size - 1 - i]))
            return pairs

        bye_count = bracket_size - n_actual
        teams_playing = teams[bye_count:]
        n_playing = len(teams_playing)
        half = n_playing // 2

        pairs = []
        for i in range(half):
            home = teams_playing[i]
            away = teams_playing[n_playing - 1 - i]
            pairs.append((home, away))

        return pairs

    def _create_full_bracket(self, tournament, stage, teams, bracket_size, first_round_pairs, options, bracket_type):
        """Build the entire bracket: round 1 matches + placeholder matches for subsequent rounds."""
        Match = self.env["federation.match"]
        start_dt = options.get("start_datetime")
        interval = options.get("interval_hours", 0)
        venue = options.get("venue", "")

        total_rounds = math.ceil(math.log2(bracket_size)) if bracket_size > 1 else 1
        n_actual = len(teams)
        bye_count = bracket_size - n_actual
        bye_teams = teams[:bye_count] if bye_count > 0 else []

        round_names = self._get_round_names(total_rounds)

        # --- Round 1: real matches ---
        round_1_matches = []
        for i, (home, away) in enumerate(first_round_pairs):
            vals = {
                "tournament_id": tournament.id,
                "stage_id": stage.id,
                "home_team_id": home.id,
                "away_team_id": away.id,
                "state": "draft",
                "round_number": 1,
                "bracket_position": i + 1,
                "bracket_type": bracket_type,
            }
            if start_dt:
                vals["date_scheduled"] = start_dt + timedelta(hours=i * interval)
            round_1_matches.append(Match.create(vals))

        all_matches = list(round_1_matches)

        # Build the feed list for round 2.
        # Each slot in feed_sources will later become one side of a round-2 match.
        # For byes, the team auto-advances (no match); for played matches, the winner advances.
        # The bracket layout is: top seeds get byes, remaining play first round.
        # Reconstruct the bracket order to properly wire sources.
        feed_sources = []
        bye_idx = 0
        match_idx = 0
        slots_in_r2 = bracket_size // 2

        for slot in range(slots_in_r2):
            # Standard bracket pairing: seed (slot+1) vs seed (bracket_size - slot)
            top_seed_pos = slot          # 0-indexed
            bot_seed_pos = bracket_size - 1 - slot

            top_is_bye = top_seed_pos < bye_count
            bot_is_bye = bot_seed_pos < bye_count

            if top_is_bye and bot_is_bye:
                # Both byes — shouldn't happen with a valid bracket but handle gracefully
                feed_sources.append({"type": "bye", "team": teams[top_seed_pos]})
                feed_sources.append({"type": "bye", "team": teams[bot_seed_pos]})
            elif top_is_bye:
                # Top seed has a bye, bottom seed's match result feeds in
                feed_sources.append({"type": "bye", "team": teams[top_seed_pos]})
                feed_sources.append({"type": "match", "match": round_1_matches[match_idx], "result": "winner"})
                match_idx += 1
            elif bot_is_bye:
                feed_sources.append({"type": "match", "match": round_1_matches[match_idx], "result": "winner"})
                match_idx += 1
                feed_sources.append({"type": "bye", "team": teams[bot_seed_pos]})
            else:
                feed_sources.append({"type": "match", "match": round_1_matches[match_idx], "result": "winner"})
                match_idx += 1

        # --- Rounds 2..N: placeholder matches ---
        prev_round_sources = feed_sources
        for rnd in range(2, total_rounds + 1):
            matches_in_round = len(prev_round_sources) // 2
            current_matches = []
            round_dt = start_dt + timedelta(hours=(rnd - 1) * 24) if start_dt else None

            for m in range(matches_in_round):
                src_a = prev_round_sources[m * 2]
                src_b = prev_round_sources[m * 2 + 1]

                vals = {
                    "tournament_id": tournament.id,
                    "stage_id": stage.id,
                    "state": "draft",
                    "round_number": rnd,
                    "bracket_position": m + 1,
                    "bracket_type": bracket_type,
                }
                if round_dt:
                    vals["date_scheduled"] = round_dt + timedelta(hours=m * interval)

                # Wire source A → home
                if src_a["type"] == "bye":
                    vals["home_team_id"] = src_a["team"].id
                else:
                    vals["source_match_1_id"] = src_a["match"].id
                    vals["source_type_1"] = src_a.get("result", "winner")

                # Wire source B → away
                if src_b["type"] == "bye":
                    vals["away_team_id"] = src_b["team"].id
                else:
                    vals["source_match_2_id"] = src_b["match"].id
                    vals["source_type_2"] = src_b.get("result", "winner")

                match = Match.create(vals)
                current_matches.append(match)
                all_matches.append(match)

            # Feed next round
            prev_round_sources = [
                {"type": "match", "match": m, "result": "winner"}
                for m in current_matches
            ]

        return all_matches

    @staticmethod
    def _get_round_names(total_rounds):
        names = {}
        names[total_rounds] = "Final"
        if total_rounds >= 2:
            names[total_rounds - 1] = "Semifinal"
        if total_rounds >= 3:
            names[total_rounds - 2] = "Quarterfinal"
        for r in range(1, total_rounds + 1):
            if r not in names:
                names[r] = f"Round {r}"
        return names
