from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestDiscipline(TransactionCase):

    @classmethod
    def setUpClass(cls):
        """Set up shared test data for the test case."""
        super().setUpClass()
        cls.club = cls.env["federation.club"].create({
            "name": "Test Club",
            "code": "TEST",
        })
        cls.team = cls.env["federation.team"].create({
            "name": "Test Team",
            "club_id": cls.club.id,
            "code": "TT",
        })
        cls.player = cls.env["federation.player"].create({
            "name": "Test Player",
            "first_name": "Test",
            "last_name": "Player",
        })
        cls.season = cls.env["federation.season"].create({
            "name": "Test Season",
            "code": "TS2024",
            "date_start": "2024-01-01",
            "date_end": "2024-12-31",
        })
        cls.tournament = cls.env["federation.tournament"].create({
            "name": "Test Tournament",
            "code": "TTOUR",
            "season_id": cls.season.id,
            "date_start": "2024-06-01",
        })
        cls.match = cls.env["federation.match"].create({
            "tournament_id": cls.tournament.id,
            "home_team_id": cls.team.id,
            "date_scheduled": "2024-06-15 15:00:00",
        })

    def test_create_incident_with_subject(self):
        """Test creating an incident with a valid subject."""
        incident = self.env["federation.match.incident"].create({
            "name": "Yellow Card Incident",
            "match_id": self.match.id,
            "player_id": self.player.id,
            "incident_type": "yellow_card",
            "description": "Player received a yellow card for foul play.",
        })
        self.assertTrue(incident.id)
        self.assertEqual(incident.status, "new")
        self.assertEqual(incident.player_id, self.player)

    def test_incident_requires_subject_reference(self):
        """Test that incident requires at least one subject reference.

        @api.constrains only fires when a constrained field is set, so we
        must explicitly set one field to False to trigger the check.
        """
        with self.assertRaises(ValidationError):
            self.env["federation.match.incident"].create({
                "name": "Bad Incident",
                "incident_type": "other",
                "description": "No subject reference provided.",
                "player_id": False,
            })

    def test_create_case_and_attach_incident(self):
        """Test creating a case and attaching an incident."""
        incident = self.env["federation.match.incident"].create({
            "name": "Test Incident",
            "match_id": self.match.id,
            "player_id": self.player.id,
            "incident_type": "misconduct",
            "description": "Player misconduct during match.",
        })
        case = self.env["federation.disciplinary.case"].create({
            "name": "Test Case",
            "subject_player_id": self.player.id,
            "summary": "Case for player misconduct.",
            "incident_ids": [(4, incident.id)],
        })
        self.assertTrue(case.id)
        self.assertEqual(case.state, "draft")
        self.assertIn(incident, case.incident_ids)

    def test_case_state_transitions(self):
        """Test case state transitions."""
        case = self.env["federation.disciplinary.case"].create({
            "name": "Test Case",
            "subject_player_id": self.player.id,
            "summary": "Test case for state transitions.",
        })
        self.assertEqual(case.state, "draft")
        
        case.action_submit_review()
        self.assertEqual(case.state, "under_review")
        
        case.action_decide()
        self.assertEqual(case.state, "decided")
        self.assertTrue(case.decided_on)
        
        case.action_mark_appealed()
        self.assertEqual(case.state, "appealed")
        
        case.action_close()
        self.assertEqual(case.state, "closed")
        self.assertTrue(case.closed_on)

    def test_review_submission_and_reopen_enforce_state_guards(self):
        """Test review submission and reopen only allow the documented states."""
        case = self.env["federation.disciplinary.case"].create({
            "name": "Review Guard Case",
            "subject_player_id": self.player.id,
            "summary": "Exercise review workflow guards.",
        })

        with self.assertRaises(ValidationError):
            case.action_reopen()
        self.assertEqual(case.state, "draft")

        case.action_submit_review()
        self.assertEqual(case.state, "under_review")

        with self.assertRaises(ValidationError):
            case.action_submit_review()

        case.action_reopen()
        self.assertEqual(case.state, "draft")

    def test_create_sanction(self):
        """Test creating a sanction."""
        case = self.env["federation.disciplinary.case"].create({
            "name": "Test Case",
            "subject_player_id": self.player.id,
            "summary": "Test case for sanction.",
        })
        sanction = self.env["federation.sanction"].create({
            "name": "Fine for Misconduct",
            "case_id": case.id,
            "sanction_type": "fine",
            "player_id": self.player.id,
            "amount": 500.00,
            "effective_date": "2024-07-01",
        })
        self.assertTrue(sanction.id)
        self.assertEqual(sanction.sanction_type, "fine")
        self.assertEqual(sanction.amount, 500.00)

    def test_create_suspension(self):
        """Test creating a suspension."""
        case = self.env["federation.disciplinary.case"].create({
            "name": "Test Case",
            "subject_player_id": self.player.id,
            "summary": "Test case for suspension.",
        })
        suspension = self.env["federation.suspension"].create({
            "name": "3-Match Suspension",
            "case_id": case.id,
            "player_id": self.player.id,
            "date_start": "2024-07-01",
            "date_end": "2024-07-31",
        })
        self.assertTrue(suspension.id)
        self.assertEqual(suspension.state, "draft")
        
        suspension.action_activate()
        self.assertEqual(suspension.state, "active")

    def test_suspension_date_validation(self):
        """Test that suspension end date must be >= start date."""
        case = self.env["federation.disciplinary.case"].create({
            "name": "Test Case",
            "subject_player_id": self.player.id,
            "summary": "Test case for suspension validation.",
        })
        with self.assertRaises(ValidationError):
            self.env["federation.suspension"].create({
                "name": "Bad Suspension",
                "case_id": case.id,
                "player_id": self.player.id,
                "date_start": "2024-07-31",
                "date_end": "2024-07-01",
            })