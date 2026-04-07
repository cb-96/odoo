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
                - rounds_count: int (how many full cycles to repeat)
                - schedule_by_round: bool (if True, schedule each round as a time block)
                - round_interval_hours: int (hours between rounds when scheduling by round)
                - start_datetime: datetime or False
                - interval_hours: int (intra-round spacing)
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
        base_rounds = self._generate_pairings(teams, options.get("double_round", False))

        repeats = int(options.get("rounds_count", 1) or 1)
        rounds = []
        for _ in range(repeats):
            rounds.extend(base_rounds)

        matches = self._create_matches(tournament, stage, rounds, options)

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

        rounds_count = n - 1
        half = n // 2
        working = list(teams)
        rounds_list = []

        for round_num in range(rounds_count):
            round_pairs = []
            for i in range(half):
                home = working[i]
                away = working[n - 1 - i]
                if home and away:
                    # Alternate home/away by round for fairness
                    if round_num % 2 == 0:
                        round_pairs.append((home, away))
                    else:
                        round_pairs.append((away, home))
            rounds_list.append(round_pairs)
            # Rotate: keep first fixed, rotate rest clockwise
            working = [working[0]] + [working[-1]] + working[1:-1]

        if double_round:
            # Append reversed rounds to provide return fixtures
            reversed_rounds = []
            for r in rounds_list:
                reversed_rounds.append([(away, home) for (home, away) in r])
            rounds_list.extend(reversed_rounds)

        return rounds_list

    def _create_matches(self, tournament, stage, rounds, options):
        """
        Create `federation.match` records from rounds (list of rounds -> list of pairs).

        Scheduling behavior depends on options:
        - If `schedule_by_round` is True and `start_datetime` is set, each round is
          scheduled at `start_datetime + round_index * round_interval_hours` and
          intra-round spacing uses `interval_hours`.
        - Otherwise matches are scheduled sequentially across all rounds using
          `interval_hours` between matches.
        """
        Match = self.env["federation.match"]
        start_dt = options.get("start_datetime")
        interval = options.get("interval_hours", 0)
        round_interval = options.get("round_interval_hours")
        venue = options.get("venue", "")
        group = options.get("group")
        schedule_by_round = bool(options.get("schedule_by_round"))

        created = []

        # Try to resolve a venue record if a venue name was provided
        Venue = self.env["federation.venue"]
        Gameday = self.env["federation.gameday"]
        venue_rec = None
        if venue:
            venue_rec = Venue.search([("name", "=", venue)], limit=1)

        if schedule_by_round and start_dt:
            # default round interval to 24h if not set
            if not round_interval:
                round_interval = interval or 24
            from datetime import timedelta
            for r_idx, round_pairs in enumerate(rounds):
                round_base = start_dt + timedelta(hours=r_idx * round_interval)

                # If we have a venue record, create/find a gameday for this round
                gameday = None
                if venue_rec:
                    gameday = Gameday.find_or_create(venue_rec.id, round_base)

                # Build annotated entries so we can alternate male/female matches
                entries = []
                for (home, away) in round_pairs:
                    if not home or not away:
                        continue
                    h_gender = getattr(home, "gender", None)
                    a_gender = getattr(away, "gender", None)
                    if h_gender == "male" and a_gender == "male":
                        g = "male"
                    elif h_gender == "female" and a_gender == "female":
                        g = "female"
                    else:
                        g = "mixed"
                    entries.append({"home": home, "away": away, "gender": g})

                # Partition and weave male/female entries to alternate genders for rest
                male = [e for e in entries if e["gender"] == "male"]
                female = [e for e in entries if e["gender"] == "female"]
                mixed = [e for e in entries if e["gender"] not in ("male", "female")]

                ordered = []
                last = None
                while male or female:
                    if last != "male" and male:
                        ordered.append(male.pop(0))
                        last = "male"
                    elif last != "female" and female:
                        ordered.append(female.pop(0))
                        last = "female"
                    elif male:
                        ordered.append(male.pop(0))
                        last = "male"
                    elif female:
                        ordered.append(female.pop(0))
                        last = "female"
                ordered.extend(mixed)

                for m_idx, entry in enumerate(ordered):
                    home = entry["home"]
                    away = entry["away"]

                    # Prevent duplicate same-category pairings on the same gameday
                    if gameday and home.category == away.category:
                        dup_count = Match.search_count([
                            ("gameday_id", "=", gameday.id),
                            ("home_team_id", "=", home.id),
                            ("away_team_id", "=", away.id),
                        ]) + Match.search_count([
                            ("gameday_id", "=", gameday.id),
                            ("home_team_id", "=", away.id),
                            ("away_team_id", "=", home.id),
                        ])
                        if dup_count:
                            raise UserError(_(
                                "Duplicate pairing for same category on gameday %s: %s vs %s"
                            ) % (gameday.name, home.name, away.name))

                    vals = {
                        "tournament_id": tournament.id,
                        "stage_id": stage.id,
                        "home_team_id": home.id,
                        "away_team_id": away.id,
                        "state": "draft",
                    }
                    if group:
                        vals["group_id"] = group.id
                    # link venue record if available (backwards-compatible)
                    if venue_rec:
                        vals["venue_id"] = venue_rec.id
                        vals["venue"] = venue_rec.name
                    if gameday:
                        vals["gameday_id"] = gameday.id

                    # intra-round spacing
                    if interval:
                        vals["date_scheduled"] = round_base + timedelta(hours=m_idx * interval)
                    else:
                        vals["date_scheduled"] = round_base

                    created.append(Match.create(vals))
        else:
            # Flatten rounds and schedule sequentially
            from datetime import timedelta
            idx = 0
            for round_pairs in rounds:
                for (home, away) in round_pairs:
                    vals = {
                        "tournament_id": tournament.id,
                        "stage_id": stage.id,
                        "home_team_id": home.id,
                        "away_team_id": away.id,
                        "state": "draft",
                    }
                    if group:
                        vals["group_id"] = group.id
                    if venue:
                        # try to attach venue record when possible
                        try:
                            venue_rec = Venue.search([("name", "=", venue)], limit=1)
                        except Exception:
                            venue_rec = None
                        if venue_rec:
                            vals["venue_id"] = venue_rec.id
                            vals["venue"] = venue_rec.name
                    if start_dt and interval:
                        vals["date_scheduled"] = start_dt + timedelta(hours=idx * interval)
                    elif start_dt:
                        vals["date_scheduled"] = start_dt
                    created.append(Match.create(vals))
                    idx += 1

        return created