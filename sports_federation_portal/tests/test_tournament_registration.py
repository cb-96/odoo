from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestTournamentRegistration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.club = cls.env["federation.club"].create({
            "name": "Portal Registration Club",
            "code": "PRC",
        })
        cls.season = cls.env["federation.season"].create({
            "name": "Portal Registration Season",
            "code": "PRS",
            "date_start": "2025-01-01",
            "date_end": "2025-12-31",
        })
        cls.eligible_team = cls.env["federation.team"].create({
            "name": "Eligible Portal Team",
            "club_id": cls.club.id,
            "code": "EPT",
            "category": "senior",
            "gender": "male",
        })
        cls.ineligible_team = cls.env["federation.team"].create({
            "name": "Ineligible Portal Team",
            "club_id": cls.club.id,
            "code": "IPT",
            "category": "senior",
            "gender": "female",
        })
        cls.tournament = cls.env["federation.tournament"].create({
            "name": "Portal Tournament",
            "code": "PT",
            "season_id": cls.season.id,
            "date_start": "2025-06-01",
            "gender": "male",
            "category": "senior",
        })

    def test_registration_accepts_eligible_team(self):
        registration = self.env["federation.tournament.registration"].create({
            "tournament_id": self.tournament.id,
            "team_id": self.eligible_team.id,
        })
        self.assertEqual(registration.team_id, self.eligible_team)

    def test_registration_rejects_ineligible_team(self):
        with self.assertRaises(ValidationError):
            self.env["federation.tournament.registration"].create({
                "tournament_id": self.tournament.id,
                "team_id": self.ineligible_team.id,
            })

    def test_registration_backend_domain_uses_eligible_teams(self):
        registration = self.env["federation.tournament.registration"].new({
            "tournament_id": self.tournament.id,
        })
        registration._compute_team_selection()

        eligible_team_ids = registration.eligible_team_ids._origin.ids
        self.assertIn(self.eligible_team.id, eligible_team_ids)
        self.assertNotIn(self.ineligible_team.id, eligible_team_ids)

        available_team_ids = registration.available_team_ids._origin.ids
        self.assertIn(self.eligible_team.id, available_team_ids)
        self.assertNotIn(self.ineligible_team.id, available_team_ids)
        self.assertIn("Ineligible Portal Team", registration.excluded_team_feedback_html)

    def test_registration_backend_feedback_explains_duplicate_team(self):
        self.env["federation.tournament.registration"].create({
            "tournament_id": self.tournament.id,
            "team_id": self.eligible_team.id,
            "state": "submitted",
        })

        registration = self.env["federation.tournament.registration"].new({
            "tournament_id": self.tournament.id,
        })
        registration._compute_team_selection()

        self.assertNotIn(self.eligible_team.id, registration.available_team_ids._origin.ids)
        self.assertIn("Already registered or currently awaiting review.", registration.excluded_team_feedback_html)