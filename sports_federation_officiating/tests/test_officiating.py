"""Tests for sports_federation_officiating: referees, certifications, match assignments."""
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestFederationReferee(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.referee = cls.env["federation.referee"].create({
            "name": "Test Referee",
            "email": "ref@example.com",
            "certification_level": "national",
        })

    def test_create_referee(self):
        self.assertTrue(self.referee.id)
        self.assertEqual(self.referee.certification_level, "national")

    def test_certification_count(self):
        self.assertEqual(self.referee.certification_count, 0)
        self.env["federation.referee.certification"].create({
            "name": "CERT-001",
            "referee_id": self.referee.id,
            "level": "national",
            "issue_date": "2024-01-01",
        })
        self.referee.invalidate_recordset()
        self.assertEqual(self.referee.certification_count, 1)


class TestRefereeCertification(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.referee = cls.env["federation.referee"].create({
            "name": "Cert Referee",
        })

    def test_create_certification(self):
        cert = self.env["federation.referee.certification"].create({
            "name": "CERT-002",
            "referee_id": self.referee.id,
            "level": "regional",
            "issue_date": "2024-03-01",
        })
        self.assertTrue(cert.id)
        self.assertTrue(cert.active)

    def test_certification_invalid_dates(self):
        with self.assertRaises(ValidationError):
            self.env["federation.referee.certification"].create({
                "name": "CERT-BAD",
                "referee_id": self.referee.id,
                "level": "local",
                "issue_date": "2024-06-01",
                "expiry_date": "2024-01-01",
            })

    def test_duplicate_certification_rejected(self):
        self.env["federation.referee.certification"].create({
            "name": "CERT-003",
            "referee_id": self.referee.id,
            "level": "national",
            "issue_date": "2024-05-01",
        })
        with self.assertRaises(Exception):
            self.env["federation.referee.certification"].create({
                "name": "CERT-003-DUP",
                "referee_id": self.referee.id,
                "level": "national",
                "issue_date": "2024-05-01",
            })
            self.env.cr.flush()


class TestMatchReferee(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.club = cls.env["federation.club"].create({
            "name": "Ref Test Club", "code": "RTC",
        })
        cls.team_a = cls.env["federation.team"].create({
            "name": "Ref Team A", "club_id": cls.club.id, "code": "RTA",
        })
        cls.team_b = cls.env["federation.team"].create({
            "name": "Ref Team B", "club_id": cls.club.id, "code": "RTB",
        })
        cls.season = cls.env["federation.season"].create({
            "name": "Ref Season", "code": "REFS24",
            "date_start": "2024-01-01", "date_end": "2024-12-31",
        })
        cls.tournament = cls.env["federation.tournament"].create({
            "name": "Ref Tournament", "code": "RTOUR",
            "season_id": cls.season.id,
            "date_start": "2024-06-01",
        })
        cls.match = cls.env["federation.match"].create({
            "tournament_id": cls.tournament.id,
            "home_team_id": cls.team_a.id,
            "away_team_id": cls.team_b.id,
            "state": "draft",
        })
        cls.referee = cls.env["federation.referee"].create({
            "name": "Match Referee",
            "certification_level": "national",
        })

    def test_assign_referee_to_match(self):
        assignment = self.env["federation.match.referee"].create({
            "match_id": self.match.id,
            "referee_id": self.referee.id,
            "role": "head",
        })
        self.assertTrue(assignment.id)
        self.assertEqual(assignment.state, "draft")
        self.assertEqual(assignment.tournament_id, self.tournament)

    def test_assignment_state_transitions(self):
        assignment = self.env["federation.match.referee"].create({
            "match_id": self.match.id,
            "referee_id": self.referee.id,
            "role": "head",
        })
        assignment.action_confirm()
        self.assertEqual(assignment.state, "confirmed")
        assignment.action_done()
        self.assertEqual(assignment.state, "done")
        assignment.action_draft()
        self.assertEqual(assignment.state, "draft")
        assignment.action_cancel()
        self.assertEqual(assignment.state, "cancelled")

    def test_duplicate_role_rejected(self):
        self.env["federation.match.referee"].create({
            "match_id": self.match.id,
            "referee_id": self.referee.id,
            "role": "head",
        })
        with self.assertRaises(Exception):
            self.env["federation.match.referee"].create({
                "match_id": self.match.id,
                "referee_id": self.referee.id,
                "role": "head",
            })
            self.env.cr.flush()

    def test_different_roles_allowed(self):
        ref2 = self.env["federation.referee"].create({
            "name": "Assistant Ref",
        })
        self.env["federation.match.referee"].create({
            "match_id": self.match.id,
            "referee_id": self.referee.id,
            "role": "head",
        })
        assignment2 = self.env["federation.match.referee"].create({
            "match_id": self.match.id,
            "referee_id": ref2.id,
            "role": "assistant_1",
        })
        self.assertTrue(assignment2.id)

    def test_assignment_count_computed(self):
        self.env["federation.match.referee"].create({
            "match_id": self.match.id,
            "referee_id": self.referee.id,
            "role": "head",
        })
        self.referee.invalidate_recordset()
        self.assertEqual(self.referee.assignment_count, 1)
