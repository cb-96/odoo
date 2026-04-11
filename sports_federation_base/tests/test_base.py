"""Tests for sports_federation_base: clubs, teams, seasons, registrations."""
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestFederationClub(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.club = cls.env["federation.club"].create({
            "name": "Test Club",
            "code": "TC01",
        })

    def test_create_club(self):
        self.assertTrue(self.club.id)
        self.assertEqual(self.club.name, "Test Club")

    def test_club_code_unique(self):
        with self.assertRaises(Exception):
            self.env["federation.club"].create({
                "name": "Duplicate Code Club",
                "code": "TC01",
            })
            self.env.cr.flush()

    def test_club_invalid_email(self):
        with self.assertRaises(ValidationError):
            self.club.write({"email": "not-an-email"})

    def test_club_valid_email(self):
        self.club.write({"email": "club@example.com"})
        self.assertEqual(self.club.email, "club@example.com")

    def test_club_team_count(self):
        self.assertEqual(self.club.team_count, 0)
        self.env["federation.team"].create({
            "name": "Team A",
            "club_id": self.club.id,
            "code": "TA",
        })
        self.club.invalidate_recordset()
        self.assertEqual(self.club.team_count, 1)

    def test_club_archive_requires_archived_teams(self):
        team = self.env["federation.team"].create({
            "name": "Archive Team",
            "club_id": self.club.id,
            "code": "AT01",
        })

        with self.assertRaises(ValidationError):
            self.club.action_archive()

        team.action_archive()
        self.club.action_archive()
        self.assertFalse(self.club.active)

        self.club.action_restore()
        self.assertTrue(self.club.active)


class TestFederationTeam(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.club = cls.env["federation.club"].create({
            "name": "Team Test Club",
            "code": "TTC",
        })
        cls.team = cls.env["federation.team"].create({
            "name": "Senior Squad",
            "club_id": cls.club.id,
            "code": "SS01",
            "category": "senior",
        })

    def test_create_team(self):
        self.assertTrue(self.team.id)
        self.assertEqual(self.team.category, "senior")

    def test_team_display_name_includes_gender(self):
        self.assertEqual(self.team.display_name, "Senior Squad (Men)")

    def test_team_code_unique(self):
        with self.assertRaises(Exception):
            self.env["federation.team"].create({
                "name": "Other Team",
                "club_id": self.club.id,
                "code": "SS01",
            })
            self.env.cr.flush()

    def test_team_name_search_by_code(self):
        results = self.env["federation.team"].name_search("SS01")
        ids = [r[0] if isinstance(r, (list, tuple)) else r.id for r in results]
        self.assertIn(self.team.id, ids)

    def test_team_archive_requires_cancelled_registrations(self):
        season = self.env["federation.season"].create({
            "name": "Archive Season",
            "code": "AS24",
            "date_start": "2024-01-01",
            "date_end": "2024-12-31",
        })
        registration = self.env["federation.season.registration"].create({
            "season_id": season.id,
            "team_id": self.team.id,
        })

        with self.assertRaises(ValidationError):
            self.team.action_archive()

        registration.action_cancel()
        self.team.action_archive()
        self.assertFalse(self.team.active)

        self.team.action_restore()
        self.assertTrue(self.team.active)


class TestFederationSeason(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.season = cls.env["federation.season"].create({
            "name": "2024-25 Season",
            "code": "S2425",
            "date_start": "2024-09-01",
            "date_end": "2025-06-30",
        })

    def test_create_season(self):
        self.assertTrue(self.season.id)
        self.assertEqual(self.season.state, "draft")

    def test_season_state_transitions(self):
        self.season.action_open()
        self.assertEqual(self.season.state, "open")
        self.season.action_close()
        self.assertEqual(self.season.state, "closed")

    def test_season_state_guards_and_archive(self):
        with self.assertRaises(ValidationError):
            self.season.action_close()

        self.season.action_open()
        with self.assertRaises(ValidationError):
            self.season.action_archive()

        self.season.action_cancel()
        self.assertEqual(self.season.state, "cancelled")
        self.season.action_draft()
        self.assertEqual(self.season.state, "draft")

        self.season.action_archive()
        self.assertFalse(self.season.active)

        self.season.action_restore()
        self.assertTrue(self.season.active)

    def test_season_invalid_dates(self):
        with self.assertRaises(ValidationError):
            self.env["federation.season"].create({
                "name": "Bad Season",
                "date_start": "2025-01-01",
                "date_end": "2024-01-01",
            })

    def test_season_same_dates_rejected(self):
        with self.assertRaises(ValidationError):
            self.env["federation.season"].create({
                "name": "Same Date Season",
                "date_start": "2025-01-01",
                "date_end": "2025-01-01",
            })


class TestFederationSeasonRegistration(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.club = cls.env["federation.club"].create({
            "name": "Reg Club", "code": "RC",
        })
        cls.team = cls.env["federation.team"].create({
            "name": "Reg Team", "club_id": cls.club.id, "code": "RT",
        })
        cls.season = cls.env["federation.season"].create({
            "name": "Reg Season", "code": "RS24",
            "date_start": "2024-01-01", "date_end": "2024-12-31",
        })

    def test_create_registration(self):
        reg = self.env["federation.season.registration"].create({
            "season_id": self.season.id,
            "team_id": self.team.id,
        })
        self.assertTrue(reg.id)
        self.assertEqual(reg.state, "draft")
        self.assertEqual(reg.club_id, self.club)

    def test_registration_state_transitions(self):
        reg = self.env["federation.season.registration"].create({
            "season_id": self.season.id,
            "team_id": self.team.id,
        })
        reg.action_confirm()
        self.assertEqual(reg.state, "confirmed")
        reg.action_cancel()
        self.assertEqual(reg.state, "cancelled")
        reg.action_draft()
        self.assertEqual(reg.state, "draft")

    def test_duplicate_registration_rejected(self):
        self.env["federation.season.registration"].create({
            "season_id": self.season.id,
            "team_id": self.team.id,
        })
        with self.assertRaises(Exception):
            self.env["federation.season.registration"].create({
                "season_id": self.season.id,
                "team_id": self.team.id,
            })
            self.env.cr.flush()
