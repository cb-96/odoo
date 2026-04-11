import logging
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
                - use_stage_gamedays: bool (if True, assign each round to an existing stage gameday)
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

    def _get_stage_gamedays(self, stage):
        Gameday = self.env.get("federation.gameday")
        if Gameday is None:
            return None
        return Gameday.search(
            [("stage_id", "=", stage.id)],
            order="sequence asc, id asc",
        )

    def _ensure_gameday_scope(self, gameday, tournament, stage):
        if not gameday or not tournament or gameday.tournament_id:
            return gameday

        vals = {"tournament_id": tournament.id}
        if stage and not gameday.stage_id:
            vals["stage_id"] = stage.id
        if not gameday.sequence:
            vals["sequence"] = self.env["federation.gameday"]._next_tournament_sequence(
                tournament.id
            )

        try:
            gameday.write(vals)
        except Exception:
            # If another process scoped the gameday concurrently, reload it.
            gameday = self.env["federation.gameday"].browse(gameday.id)

        return gameday

    def _get_ordered_round_entries(self, round_pairs):
        entries = []
        for home, away in round_pairs:
            if not home or not away:
                continue
            h_gender = getattr(home, "gender", None)
            a_gender = getattr(away, "gender", None)
            if h_gender == "male" and a_gender == "male":
                gender = "male"
            elif h_gender == "female" and a_gender == "female":
                gender = "female"
            else:
                gender = "mixed"
            entries.append({"home": home, "away": away, "gender": gender})

        male = [entry for entry in entries if entry["gender"] == "male"]
        female = [entry for entry in entries if entry["gender"] == "female"]
        mixed = [entry for entry in entries if entry["gender"] not in ("male", "female")]

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
        return ordered

    def _check_duplicate_pairing_on_gameday(self, Match, gameday, home, away):
        if not gameday or home.category != away.category:
            return

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

    def _create_matches(self, tournament, stage, rounds, options):
        """
        Create `federation.match` records from rounds (list of rounds -> list of pairs).

        Scheduling behavior depends on options:
        - If `use_stage_gamedays` is True, each generated round is assigned to the
          next existing gameday on the selected stage, ordered by sequence.
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
        use_stage_gamedays = bool(options.get("use_stage_gamedays"))
        schedule_by_round = bool(options.get("schedule_by_round"))

        created = []

        # Try to resolve a venue record if a venue name was provided
        Venue = self.env.get("federation.venue")
        Gameday = self.env.get("federation.gameday")
        venue_rec = None
        if venue and Venue is not None:
            venue_rec = Venue.search([("name", "=", venue)], limit=1)

        if use_stage_gamedays:
            from datetime import timedelta

            stage_gamedays = self._get_stage_gamedays(stage)
            if stage_gamedays is None:
                raise UserError(_(
                    "Existing stage gamedays require the venues module to be installed."
                ))
            if not stage_gamedays:
                raise UserError(_(
                    "No gamedays were found on the selected stage. Add stage gamedays or disable Use Existing Stage Gamedays."
                ))
            if len(stage_gamedays) < len(rounds):
                raise UserError(_(
                    "This stage has %(available)s gamedays, but %(required)s rounds will be generated. Add more stage gamedays or disable Use Existing Stage Gamedays."
                ) % {
                    "available": len(stage_gamedays),
                    "required": len(rounds),
                })

            for r_idx, round_pairs in enumerate(rounds):
                gameday = stage_gamedays[r_idx]
                ordered = self._get_ordered_round_entries(round_pairs)
                round_base = gameday.start_datetime or False
                round_number = r_idx + 1

                for m_idx, entry in enumerate(ordered):
                    home = entry["home"]
                    away = entry["away"]
                    self._check_duplicate_pairing_on_gameday(Match, gameday, home, away)

                    vals = {
                        "tournament_id": tournament.id,
                        "stage_id": stage.id,
                        "home_team_id": home.id,
                        "away_team_id": away.id,
                        "gameday_id": gameday.id,
                        "round_number": round_number,
                        "state": "draft",
                    }
                    if group:
                        vals["group_id"] = group.id
                    if round_base:
                        if interval:
                            vals["date_scheduled"] = round_base + timedelta(hours=m_idx * interval)
                        else:
                            vals["date_scheduled"] = round_base

                    created.append(Match.create(vals))
        elif schedule_by_round and start_dt:
            # default round interval to 24h if not set
            if not round_interval:
                round_interval = interval or 24
            from datetime import timedelta
            for r_idx, round_pairs in enumerate(rounds):
                round_base = start_dt + timedelta(hours=r_idx * round_interval)
                round_number = r_idx + 1

                # If we have a venue record, create/find a gameday for this round
                gameday = None
                if venue_rec and Gameday is not None:
                    gameday = Gameday.find_or_create(venue_rec.id, round_base)
                    gameday = self._ensure_gameday_scope(gameday, tournament, stage)

                ordered = self._get_ordered_round_entries(round_pairs)

                for m_idx, entry in enumerate(ordered):
                    home = entry["home"]
                    away = entry["away"]

                    self._check_duplicate_pairing_on_gameday(Match, gameday, home, away)

                    vals = {
                        "tournament_id": tournament.id,
                        "stage_id": stage.id,
                        "home_team_id": home.id,
                        "away_team_id": away.id,
                        "round_number": round_number,
                        "state": "draft",
                    }
                    if group:
                        vals["group_id"] = group.id
                    if venue_rec:
                        vals["venue_id"] = venue_rec.id
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
            for r_idx, round_pairs in enumerate(rounds):
                round_number = r_idx + 1
                for (home, away) in round_pairs:
                    vals = {
                        "tournament_id": tournament.id,
                        "stage_id": stage.id,
                        "home_team_id": home.id,
                        "away_team_id": away.id,
                        "round_number": round_number,
                        "state": "draft",
                    }
                    if group:
                        vals["group_id"] = group.id
                    if venue and Venue is not None:
                        # try to attach venue record when possible
                        venue_rec = Venue.search([("name", "=", venue)], limit=1)
                        if venue_rec:
                            vals["venue_id"] = venue_rec.id
                    if start_dt and interval:
                        vals["date_scheduled"] = start_dt + timedelta(hours=idx * interval)
                    elif start_dt:
                        vals["date_scheduled"] = start_dt
                    created.append(Match.create(vals))
                    idx += 1

        return created