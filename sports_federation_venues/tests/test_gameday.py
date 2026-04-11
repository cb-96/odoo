"""
Tests: federation.gameday model — no-duplicate pairing constraint and
       find_or_create grouping behaviour.

Coverage:
- ``find_or_create`` returns the same gameday record for the same venue/day.
- ``find_or_create`` creates a new gameday for a different day.
- ``_check_no_duplicate_pairings_on_gameday`` raises ValidationError when
  the same two teams of the same category are assigned the same gameday.
- Cross-category pairings are allowed on the same gameday (different category
  = constraint not triggered).
- A reversed pairing (A vs B and B vs A) on the same gameday is also rejected.
- schedule_by_round behavior: matches created via the round-robin service with
  ``schedule_by_round=True`` each get a gameday that groups by venue/round date.
"""
from datetime import datetime, timedelta
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestGameday(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.club = cls.env["federation.club"].create({
            "name": "Gameday Test Club",
            "code": "GDC",
        })
        cls.venue = cls.env["federation.venue"].create({
            "name": "Gameday Arena",
            "city": "Test City",
        })
        cls.venue2 = cls.env["federation.venue"].create({
            "name": "Secondary Arena",
            "city": "Other City",
        })
        # Two teams in same category (senior) → duplicate pairing is rejected
        cls.team_senior_a = cls.env["federation.team"].create({
            "name": "Senior A",
            "club_id": cls.club.id,
            "code": "SA",
            "category": "senior",
        })
        cls.team_senior_b = cls.env["federation.team"].create({
            "name": "Senior B",
            "club_id": cls.club.id,
            "code": "SB",
            "category": "senior",
        })
        # Two teams in different category → no constraint between them
        cls.team_youth_a = cls.env["federation.team"].create({
            "name": "Youth A",
            "club_id": cls.club.id,
            "code": "YA",
            "category": "youth",
        })
        cls.season = cls.env["federation.season"].create({
            "name": "Gameday Season",
            "code": "GS24",
            "date_start": "2024-01-01",
            "date_end": "2024-12-31",
        })
        cls.tournament = cls.env["federation.tournament"].create({
            "name": "Gameday Tournament",
            "code": "GDT",
            "season_id": cls.season.id,
            "date_start": "2024-06-01",
        })
        cls.group_stage = cls.env["federation.tournament.stage"].create({
            "name": "Group Phase",
            "tournament_id": cls.tournament.id,
            "stage_type": "group",
        })
        cls.knockout_stage = cls.env["federation.tournament.stage"].create({
            "name": "Knockout Phase",
            "tournament_id": cls.tournament.id,
            "sequence": 20,
            "stage_type": "knockout",
        })

    # ------------------------------------------------------------------
    # find_or_create tests
    # ------------------------------------------------------------------

    def test_find_or_create_creates_gameday(self):
        """find_or_create should create a new gameday for a new venue/day."""
        start_dt = datetime(2024, 6, 1, 9, 0)
        gameday = self.env["federation.gameday"].find_or_create(self.venue.id, start_dt)
        self.assertTrue(gameday.id)
        self.assertEqual(gameday.venue_id, self.venue)

    def test_find_or_create_returns_existing_same_day(self):
        """find_or_create returns the same gameday for different times on the same day."""
        start_dt_morning = datetime(2024, 6, 10, 9, 0)
        start_dt_afternoon = datetime(2024, 6, 10, 14, 0)
        gd1 = self.env["federation.gameday"].find_or_create(self.venue.id, start_dt_morning)
        gd2 = self.env["federation.gameday"].find_or_create(self.venue.id, start_dt_afternoon)
        self.assertEqual(gd1.id, gd2.id, "Same venue, same day should reuse the same gameday.")

    def test_find_or_create_different_day_creates_new(self):
        """find_or_create creates a new gameday for a different calendar day."""
        dt_day1 = datetime(2024, 6, 20, 10, 0)
        dt_day2 = datetime(2024, 6, 21, 10, 0)
        gd1 = self.env["federation.gameday"].find_or_create(self.venue.id, dt_day1)
        gd2 = self.env["federation.gameday"].find_or_create(self.venue.id, dt_day2)
        self.assertNotEqual(gd1.id, gd2.id, "Different days should produce different gamedays.")

    def test_find_or_create_different_venue_creates_new(self):
        """find_or_create creates a new gameday for the same day but a different venue."""
        dt = datetime(2024, 6, 25, 10, 0)
        gd1 = self.env["federation.gameday"].find_or_create(self.venue.id, dt)
        gd2 = self.env["federation.gameday"].find_or_create(self.venue2.id, dt)
        self.assertNotEqual(gd1.id, gd2.id, "Different venues should have separate gamedays.")

    def test_find_or_create_no_venue_returns_false(self):
        """find_or_create returns False when venue_id is not provided."""
        result = self.env["federation.gameday"].find_or_create(False, datetime(2024, 7, 1, 10, 0))
        self.assertFalse(result)

    def test_generate_planned_gamedays_creates_numbered_slots(self):
        """Tournament planning should create numbered gameday slots without venue details."""
        self.tournament.planned_gameday_total = 5

        self.tournament.action_generate_planned_gamedays()

        gamedays = self.tournament.gameday_ids.sorted("sequence")
        self.assertEqual(gamedays.mapped("sequence"), [1, 2, 3, 4, 5])
        self.assertTrue(all(not gameday.venue_id for gameday in gamedays))

        gamedays.filtered(lambda gameday: gameday.sequence <= 4).write(
            {"stage_id": self.group_stage.id}
        )
        gamedays.filtered(lambda gameday: gameday.sequence == 5).write(
            {"stage_id": self.knockout_stage.id}
        )

        self.group_stage.invalidate_recordset()
        self.knockout_stage.invalidate_recordset()
        self.assertEqual(self.group_stage.gameday_count, 4)
        self.assertEqual(self.knockout_stage.gameday_count, 1)

    # ------------------------------------------------------------------
    # No-duplicate pairing constraint tests
    # ------------------------------------------------------------------

    def _make_gameday(self, date=None):
        if date is None:
            date = datetime(2024, 8, 1, 10, 0)
        return self.env["federation.gameday"].find_or_create(self.venue.id, date)

    def test_same_category_pairing_allowed_once(self):
        """A pairing between two same-category teams on a gameday is allowed once."""
        gameday = self._make_gameday(datetime(2024, 8, 5, 10, 0))
        match = self.env["federation.match"].create({
            "tournament_id": self.tournament.id,
            "home_team_id": self.team_senior_a.id,
            "away_team_id": self.team_senior_b.id,
            "gameday_id": gameday.id,
            "state": "draft",
        })
        self.assertTrue(match.id)

    def test_duplicate_same_category_pairing_rejected(self):
        """Creating the same pairing twice on the same gameday raises ValidationError."""
        gameday = self._make_gameday(datetime(2024, 8, 10, 10, 0))
        self.env["federation.match"].create({
            "tournament_id": self.tournament.id,
            "home_team_id": self.team_senior_a.id,
            "away_team_id": self.team_senior_b.id,
            "gameday_id": gameday.id,
            "state": "draft",
        })
        with self.assertRaises(ValidationError):
            self.env["federation.match"].create({
                "tournament_id": self.tournament.id,
                "home_team_id": self.team_senior_a.id,
                "away_team_id": self.team_senior_b.id,
                "gameday_id": gameday.id,
                "state": "draft",
            })

    def test_reversed_pairing_on_same_gameday_rejected(self):
        """B vs A on the same gameday as A vs B (same category) is also rejected."""
        gameday = self._make_gameday(datetime(2024, 8, 15, 10, 0))
        self.env["federation.match"].create({
            "tournament_id": self.tournament.id,
            "home_team_id": self.team_senior_a.id,
            "away_team_id": self.team_senior_b.id,
            "gameday_id": gameday.id,
            "state": "draft",
        })
        with self.assertRaises(ValidationError):
            self.env["federation.match"].create({
                "tournament_id": self.tournament.id,
                "home_team_id": self.team_senior_b.id,
                "away_team_id": self.team_senior_a.id,
                "gameday_id": gameday.id,
                "state": "draft",
            })

    def test_cross_category_pairing_allowed_on_same_gameday(self):
        """Senior A vs Youth A can share a gameday with Senior A vs Senior B."""
        gameday = self._make_gameday(datetime(2024, 8, 20, 10, 0))
        # senior A vs senior B
        self.env["federation.match"].create({
            "tournament_id": self.tournament.id,
            "home_team_id": self.team_senior_a.id,
            "away_team_id": self.team_senior_b.id,
            "gameday_id": gameday.id,
            "state": "draft",
        })
        # senior A vs youth A — different categories, no constraint
        match2 = self.env["federation.match"].create({
            "tournament_id": self.tournament.id,
            "home_team_id": self.team_senior_a.id,
            "away_team_id": self.team_youth_a.id,
            "gameday_id": gameday.id,
            "state": "draft",
        })
        self.assertTrue(match2.id, "Cross-category pairing should be allowed.")

    def test_same_pairing_on_different_gamedays_allowed(self):
        """The same two teams can play on separate gamedays (different rounds)."""
        gd1 = self._make_gameday(datetime(2024, 9, 1, 10, 0))
        gd2 = self._make_gameday(datetime(2024, 9, 8, 10, 0))
        m1 = self.env["federation.match"].create({
            "tournament_id": self.tournament.id,
            "home_team_id": self.team_senior_a.id,
            "away_team_id": self.team_senior_b.id,
            "gameday_id": gd1.id,
            "state": "draft",
        })
        m2 = self.env["federation.match"].create({
            "tournament_id": self.tournament.id,
            "home_team_id": self.team_senior_b.id,
            "away_team_id": self.team_senior_a.id,
            "gameday_id": gd2.id,
            "state": "draft",
        })
        self.assertTrue(m1.id)
        self.assertTrue(m2.id)

    def test_no_gameday_allows_duplicate_teams(self):
        """Without a gameday set the constraint is not evaluated."""
        m1 = self.env["federation.match"].create({
            "tournament_id": self.tournament.id,
            "home_team_id": self.team_senior_a.id,
            "away_team_id": self.team_senior_b.id,
            "state": "draft",
        })
        m2 = self.env["federation.match"].create({
            "tournament_id": self.tournament.id,
            "home_team_id": self.team_senior_a.id,
            "away_team_id": self.team_senior_b.id,
            "state": "draft",
        })
        self.assertTrue(m1.id)
        self.assertTrue(m2.id)

    def test_match_gameday_assignment_inherits_scope_and_venue(self):
        """Assigning a planned gameday should backfill tournament, stage, and venue."""
        gameday = self.env["federation.gameday"].create({
            "tournament_id": self.tournament.id,
            "stage_id": self.group_stage.id,
            "sequence": 9,
            "start_datetime": datetime(2024, 9, 15, 10, 0),
            "venue_id": self.venue.id,
        })

        match = self.env["federation.match"].create({
            "home_team_id": self.team_senior_a.id,
            "away_team_id": self.team_senior_b.id,
            "gameday_id": gameday.id,
            "state": "draft",
        })

        self.assertEqual(match.tournament_id, self.tournament)
        self.assertEqual(match.stage_id, self.group_stage)
        self.assertEqual(match.venue_id, self.venue)

    def test_match_rejects_conflicting_gameday_scope(self):
        """A match cannot use a gameday from another tournament or stage."""
        other_tournament = self.env["federation.tournament"].create({
            "name": "Other Gameday Tournament",
            "code": "OGT",
            "season_id": self.season.id,
            "date_start": "2024-08-01",
        })
        other_stage = self.env["federation.tournament.stage"].create({
            "name": "Other Stage",
            "tournament_id": other_tournament.id,
            "stage_type": "group",
        })
        gameday = self.env["federation.gameday"].create({
            "tournament_id": self.tournament.id,
            "stage_id": self.group_stage.id,
            "sequence": 10,
            "venue_id": self.venue.id,
        })

        with self.assertRaises(ValidationError):
            self.env["federation.match"].create({
                "tournament_id": other_tournament.id,
                "stage_id": other_stage.id,
                "home_team_id": self.team_senior_a.id,
                "away_team_id": self.team_senior_b.id,
                "gameday_id": gameday.id,
                "venue_id": self.venue.id,
                "state": "draft",
            })

    # ------------------------------------------------------------------
    # schedule_by_round integration test (uses round_robin service)
    # ------------------------------------------------------------------

    def test_schedule_by_round_creates_gamedays(self):
        """Round-robin schedule_by_round=True assigns a gameday per round at the venue."""
        has_engine = bool(self.env.get("federation.round.robin.service"))
        if not has_engine:
            self.skipTest("sports_federation_competition_engine not installed.")

        stage = self.env["federation.tournament.stage"].create({
            "name": "Gameday RR Stage",
            "tournament_id": self.tournament.id,
        })
        team_c = self.env["federation.team"].create({"name": "GD Team C", "club_id": self.club.id, "code": "GC"})
        team_d = self.env["federation.team"].create({"name": "GD Team D", "club_id": self.club.id, "code": "GD"})
        part_c = self.env["federation.tournament.participant"].create({
            "tournament_id": self.tournament.id,
            "team_id": team_c.id,
            "stage_id": stage.id,
        })
        part_d = self.env["federation.tournament.participant"].create({
            "tournament_id": self.tournament.id,
            "team_id": team_d.id,
            "stage_id": stage.id,
        })

        # Tournament must be open/in_progress
        self.tournament.state = "open"

        service = self.env["federation.round.robin.service"]
        start_dt = datetime(2024, 10, 1, 9, 0)
        matches = service.generate(
            tournament=self.tournament,
            stage=stage,
            participants=[part_c, part_d],
            options={
                "double_round": False,
                "schedule_by_round": True,
                "start_datetime": start_dt,
                "round_interval_hours": 24,
                "interval_hours": 2,
                "venue": self.venue.name,
                "overwrite": True,
            },
        )

        # There should be 1 round with 1 match for 2 teams
        self.assertEqual(len(matches), 1)
        # The match has a gameday assigned
        match = matches[0]
        self.assertTrue(match.gameday_id, "Match should have a gameday when schedule_by_round=True.")
        self.assertEqual(match.gameday_id.venue_id, self.venue)

    def test_schedule_by_round_reuses_one_gameday_per_round(self):
        """Each round shares one gameday when multiple matches are scheduled at the same venue."""
        has_engine = bool(self.env.get("federation.round.robin.service"))
        if not has_engine:
            self.skipTest("sports_federation_competition_engine not installed.")

        stage = self.env["federation.tournament.stage"].create({
            "name": "Grouped RR Stage",
            "tournament_id": self.tournament.id,
        })
        extra_team_names = [
            ("GD Team C", "GC"),
            ("GD Team D", "GD"),
        ]
        extra_teams = [
            self.env["federation.team"].create(
                {
                    "name": name,
                    "club_id": self.club.id,
                    "code": code,
                    "category": "senior",
                }
            )
            for name, code in extra_team_names
        ]
        participants = []
        for team in [self.team_senior_a, self.team_senior_b] + extra_teams:
            participants.append(
                self.env["federation.tournament.participant"].create(
                    {
                        "tournament_id": self.tournament.id,
                        "team_id": team.id,
                        "stage_id": stage.id,
                    }
                )
            )

        self.tournament.state = "open"

        service = self.env["federation.round.robin.service"]
        start_dt = datetime(2024, 11, 1, 9, 0)
        matches = service.generate(
            tournament=self.tournament,
            stage=stage,
            participants=participants,
            options={
                "double_round": False,
                "schedule_by_round": True,
                "start_datetime": start_dt,
                "round_interval_hours": 24,
                "interval_hours": 2,
                "venue": self.venue.name,
                "overwrite": True,
            },
        )

        self.assertEqual(len(matches), 6)
        gameday_groups = {}
        for match in matches:
            self.assertTrue(match.gameday_id)
            gameday_groups.setdefault(match.gameday_id.id, []).append(match)

        self.assertEqual(len(gameday_groups), 3, "Four teams should produce 3 round-based gamedays.")
        self.assertTrue(
            all(len(group) == 2 for group in gameday_groups.values()),
            "Each round should reuse one gameday for its two matches.",
        )

    def test_round_robin_wizard_uses_existing_stage_gamedays(self):
        """The wizard can assign each generated round to an existing stage gameday."""
        has_engine = self.env.get("federation.round.robin.wizard") is not None
        if not has_engine:
            self.skipTest("sports_federation_competition_engine not installed.")

        rule_set = self.env["federation.rule.set"].create({
            "name": "Existing Gameday Rule Set",
            "code": "EGRS",
        })
        self.tournament.rule_set_id = rule_set.id
        self.tournament.state = "open"

        team_c = self.env["federation.team"].create({
            "name": "GD Existing C",
            "club_id": self.club.id,
            "code": "GEC",
            "category": "senior",
        })
        team_d = self.env["federation.team"].create({
            "name": "GD Existing D",
            "club_id": self.club.id,
            "code": "GED",
            "category": "senior",
        })

        participants = self.env["federation.tournament.participant"]
        for index, team in enumerate(
            [self.team_senior_a, self.team_senior_b, team_c, team_d],
            start=1,
        ):
            participants |= self.env["federation.tournament.participant"].create({
                "tournament_id": self.tournament.id,
                "stage_id": self.group_stage.id,
                "team_id": team.id,
                "state": "confirmed",
                "seed": index,
            })

        gameday_dates = [
            datetime(2024, 12, 1, 9, 0),
            datetime(2024, 12, 8, 9, 0),
            datetime(2024, 12, 15, 9, 0),
        ]
        stage_gamedays = self.env["federation.gameday"]
        for sequence, start_dt in enumerate(gameday_dates, start=1):
            stage_gamedays |= self.env["federation.gameday"].create({
                "tournament_id": self.tournament.id,
                "stage_id": self.group_stage.id,
                "sequence": sequence,
                "start_datetime": start_dt,
                "venue_id": self.venue.id,
            })

        wizard = self.env["federation.round.robin.wizard"].create({
            "tournament_id": self.tournament.id,
            "stage_id": self.group_stage.id,
            "use_all_participants": True,
            "round_type": "single",
            "rounds_count": 1,
            "use_stage_gamedays": True,
            "interval_hours": 2,
            "overwrite": True,
        })

        wizard.action_generate()

        matches = self.env["federation.match"].search([
            ("tournament_id", "=", self.tournament.id),
            ("stage_id", "=", self.group_stage.id),
        ])
        self.assertEqual(len(matches), 6)

        used_gamedays = matches.mapped("gameday_id").sorted("sequence")
        self.assertEqual(used_gamedays.ids, stage_gamedays.ids)
        self.assertTrue(all(match.venue_id == self.venue for match in matches))

        for gameday, start_dt in zip(stage_gamedays, gameday_dates):
            gameday_matches = matches.filtered(lambda match: match.gameday_id == gameday)
            self.assertEqual(len(gameday_matches), 2)
            self.assertEqual(
                sorted(gameday_matches.mapped("date_scheduled")),
                [start_dt, start_dt + timedelta(hours=2)],
            )
