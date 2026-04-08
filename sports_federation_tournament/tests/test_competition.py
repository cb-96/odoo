from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestFederationCompetition(TransactionCase):
    """Tests for federation.competition model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.season = cls.env["federation.season"].create({
            "name": "2025-2026",
            "date_start": "2025-09-01",
            "date_end": "2026-06-30",
        })

    def test_create_competition(self):
        """Test creating a basic competition."""
        comp = self.env["federation.competition"].create({
            "name": "Premier League",
            "code": "PL",
            "competition_type": "league",
            "season_id": self.season.id,
        })
        self.assertEqual(comp.name, "Premier League")
        self.assertEqual(comp.code, "PL")
        self.assertEqual(comp.competition_type, "league")
        self.assertEqual(comp.state, "draft")

    def test_competition_state_transitions(self):
        """Test state transitions."""
        comp = self.env["federation.competition"].create({
            "name": "Test Cup",
            "competition_type": "cup",
        })
        self.assertEqual(comp.state, "draft")

        comp.action_activate()
        self.assertEqual(comp.state, "active")

        comp.action_close()
        self.assertEqual(comp.state, "closed")

        comp.action_draft()
        self.assertEqual(comp.state, "draft")

    def test_competition_code_unique(self):
        """Test that competition code must be unique."""
        self.env["federation.competition"].create({
            "name": "Comp 1",
            "code": "UNIQUE",
        })
        with self.assertRaises(Exception):
            self.env["federation.competition"].create({
                "name": "Comp 2",
                "code": "UNIQUE",
            })

    def test_competition_rule_set_link(self):
        """Test linking a competition to a rule set."""
        rule_set = self.env["federation.rule.set"].create({
            "name": "Standard Rules",
            "code": "STD",
            "points_win": 3,
            "points_draw": 1,
            "points_loss": 0,
        })
        comp = self.env["federation.competition"].create({
            "name": "League A",
            "competition_type": "league",
            "rule_set_id": rule_set.id,
        })
        self.assertEqual(comp.rule_set_id, rule_set)

    def test_competition_tournament_count(self):
        """Test tournament count computation."""
        comp = self.env["federation.competition"].create({
            "name": "Comp with Tournaments",
            "competition_type": "league",
        })
        self.assertEqual(comp.tournament_count, 0)

        # Create a tournament linked to this competition
        self.env["federation.tournament"].create({
            "name": "Tournament 1",
            "date_start": "2025-09-01",
            "competition_id": comp.id,
        })
        comp._compute_tournament_count()
        self.assertEqual(comp.tournament_count, 1)