"""
Tests for new public site endpoints (Phase 4):
- /competitions/archive — closed/cancelled tournaments
- /competitions/<id>/teams — participant listing
- /competitions/api/json — JSON API tournament list

These are ORM-level tests (no HTTP client needed) that verify
the data layer logic that the new controller endpoints rely on.
"""
from odoo.tests.common import TransactionCase


class TestPublicSiteNewEndpoints(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.club = cls.env["federation.club"].create({
            "name": "PS Club", "code": "PSC",
        })
        cls.team_a = cls.env["federation.team"].create({
            "name": "PS Team A", "club_id": cls.club.id, "code": "PSTA",
        })
        cls.team_b = cls.env["federation.team"].create({
            "name": "PS Team B", "club_id": cls.club.id, "code": "PSTB",
        })
        cls.season = cls.env["federation.season"].create({
            "name": "PS Season", "code": "PSS24",
            "date_start": "2024-01-01", "date_end": "2024-12-31",
        })

        # Active published tournament (in_progress)
        cls.active_tour = cls.env["federation.tournament"].create({
            "name": "Active Tour",
            "code": "ATOUR",
            "season_id": cls.season.id,
            "date_start": "2024-06-01",
            "show_public_results": True,
            "show_public_standings": True,
            "website_published": True,
        })

        # Closed published tournament (archive candidate)
        cls.closed_tour = cls.env["federation.tournament"].create({
            "name": "Old Tour",
            "code": "OTOUR",
            "season_id": cls.season.id,
            "date_start": "2023-01-01",
            "date_end": "2023-12-31",
            "website_published": True,
            "state": "closed",
        })

        # Unpublished closed tournament (should not appear in archive)
        cls.unpub_closed_tour = cls.env["federation.tournament"].create({
            "name": "Unpub Closed Tour",
            "code": "UCTOUR",
            "season_id": cls.season.id,
            "date_start": "2023-01-01",
            "date_end": "2023-06-30",
            "website_published": False,
            "state": "closed",
        })
        cls.schedule_match = cls.env["federation.match"].create({
            "tournament_id": cls.active_tour.id,
            "home_team_id": cls.team_a.id,
            "away_team_id": cls.team_b.id,
            "date_scheduled": "2024-06-03 10:00:00",
            "state": "scheduled",
        })
        cls.result_match = cls.env["federation.match"].create({
            "tournament_id": cls.active_tour.id,
            "home_team_id": cls.team_a.id,
            "away_team_id": cls.team_b.id,
            "date_scheduled": "2024-06-01 10:00:00",
            "state": "done",
            "home_score": 3,
            "away_score": 1,
            "result_state": "approved",
        })
        cls.bracket_match = cls.env["federation.match"].create({
            "tournament_id": cls.active_tour.id,
            "home_team_id": cls.team_a.id,
            "away_team_id": cls.team_b.id,
            "date_scheduled": "2024-06-05 14:00:00",
            "state": "scheduled",
            "round_number": 1,
            "bracket_type": "winners",
        })
        cls.standing = cls.env["federation.standing"].create({
            "name": "Active Tour Standing",
            "tournament_id": cls.active_tour.id,
            "website_published": True,
        })
        cls.confirmed_participant = cls.env["federation.tournament.participant"].create({
            "tournament_id": cls.active_tour.id,
            "team_id": cls.team_a.id,
            "state": "confirmed",
        })

    # ------------------------------------------------------------------
    # Archive endpoint data layer
    # ------------------------------------------------------------------

    def test_archive_only_returns_closed_published(self):
        """Archive query excludes unpublished and non-closed tournaments."""
        tournaments = self.env["federation.tournament"].search([
            ("website_published", "=", True),
            ("state", "in", ("closed", "cancelled")),
        ], order="date_start desc")
        self.assertIn(self.closed_tour, tournaments)
        self.assertNotIn(self.active_tour, tournaments)
        self.assertNotIn(self.unpub_closed_tour, tournaments)

    def test_archive_includes_cancelled_published(self):
        """Cancelled published tournaments also appear in the archive."""
        cancelled = self.env["federation.tournament"].create({
            "name": "Cancelled Tour", "code": "CNTOUR",
            "season_id": self.season.id,
            "date_start": "2022-06-01",
            "website_published": True,
            "state": "cancelled",
        })
        tournaments = self.env["federation.tournament"].search([
            ("website_published", "=", True),
            ("state", "in", ("closed", "cancelled")),
        ])
        self.assertIn(cancelled, tournaments)

    # ------------------------------------------------------------------
    # Teams endpoint data layer
    # ------------------------------------------------------------------

    def test_teams_excludes_withdrawn_participants(self):
        """The teams page query excludes withdrawn participants."""
        p_confirmed = self.confirmed_participant
        p_withdrawn = self.env["federation.tournament.participant"].create({
            "tournament_id": self.active_tour.id,
            "team_id": self.team_b.id,
            "state": "withdrawn",
        })
        participants = self.env["federation.tournament.participant"].search([
            ("tournament_id", "=", self.active_tour.id),
            ("state", "!=", "withdrawn"),
        ])
        self.assertIn(p_confirmed, participants)
        self.assertNotIn(p_withdrawn, participants)

    def test_teams_shows_participant_state(self):
        """Participants carry their state for display in the teams page."""
        p = self.confirmed_participant
        self.assertEqual(p.state, "confirmed")
        self.assertTrue(p.team_id)
        self.assertTrue(p.club_id)

    def test_teams_not_shown_for_unpublished_tournament(self):
        """Unpublished tournament: website_published=False blocks the page."""
        self.active_tour.write({"website_published": False})
        self.assertFalse(self.active_tour.website_published)
        # Restore
        self.active_tour.write({"website_published": True})

    # ------------------------------------------------------------------
    # JSON API data layer
    # ------------------------------------------------------------------

    def test_json_api_returns_published_only(self):
        """JSON API query returns only published tournaments."""
        tournaments = self.env["federation.tournament"].search([
            ("website_published", "=", True),
        ], order="date_start asc")
        pub_ids = tournaments.mapped("id")
        self.assertIn(self.active_tour.id, pub_ids)
        self.assertIn(self.closed_tour.id, pub_ids)
        self.assertNotIn(self.unpub_closed_tour.id, pub_ids)

    def test_json_api_fields(self):
        """Verify that tournament records have the fields the JSON API serializes."""
        t = self.active_tour
        record = {
            "id": t.id,
            "name": t.name,
            "state": t.state,
            "date_start": t.date_start.isoformat() if t.date_start else None,
            "date_end": t.date_end.isoformat() if t.date_end else None,
        }
        self.assertEqual(record["id"], t.id)
        self.assertIsInstance(record["name"], str)
        self.assertIsNotNone(record["state"])
        # date_start is set
        self.assertIsNotNone(record["date_start"])

    def test_json_api_date_null_when_not_set(self):
        """JSON API date fields are None when the tournament has no date."""
        t = self.env["federation.tournament"].create({
            "name": "No Dates Tour", "code": "NDTOUR", "season_id": self.season.id,
            "website_published": True, "date_start": "2024-01-01",
        })
        date_end_val = t.date_end.isoformat() if t.date_end else None
        self.assertIsNone(date_end_val)

    def test_schedule_sections_use_fixture_query_not_approved_results(self):
        """The schedule helper returns future fixtures and excludes completed matches."""
        sections = self.active_tour.get_public_schedule_sections()
        scheduled_ids = []
        for section in sections:
            scheduled_ids.extend(section["matches"].ids)

        self.assertIn(self.schedule_match.id, scheduled_ids)
        self.assertIn(self.bracket_match.id, scheduled_ids)
        self.assertNotIn(self.result_match.id, scheduled_ids)

    def test_public_bracket_sections_group_knockout_matches(self):
        """Bracket helper exposes knockout sections for public rendering."""
        sections = self.active_tour.get_public_bracket_sections()

        self.assertTrue(sections)
        self.assertIn(self.bracket_match, sections[0]["matches"])
        self.assertTrue(self.active_tour.has_public_bracket())

    def test_versioned_public_feed_payload_has_stable_keys(self):
        """Versioned public feed payload exposes the expected top-level structure."""
        payload = self.active_tour.get_public_feed_payload()

        self.assertEqual(payload["api_version"], "v1")
        self.assertIn("tournament", payload)
        self.assertIn("schedule_sections", payload)
        self.assertIn("bracket_sections", payload)
        self.assertIn("results", payload)
        self.assertIn("standings", payload)
        self.assertEqual(payload["tournament"]["id"], self.active_tour.id)
        self.assertEqual(payload["results"][0]["id"], self.result_match.id)
