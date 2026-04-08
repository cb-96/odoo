from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestFederationCompetition(TransactionCase):
    """Tests for federation.competition (template) and federation.competition.edition models."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.season = cls.env["federation.season"].create({
            "name": "2025-2026",
            "date_start": "2025-09-01",
            "date_end": "2026-06-30",
        })

    def test_create_competition(self):
        """Test creating a basic competition template."""
        comp = self.env["federation.competition"].create({
            "name": "Premier League",
            "code": "PL",
            "competition_type": "league",
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

    def test_competition_edition_count(self):
        """Test edition count computation on competition template."""
        comp = self.env["federation.competition"].create({
            "name": "Comp with Editions",
            "competition_type": "league",
        })
        self.assertEqual(comp.edition_count, 0)

        # Create an edition linked to this competition
        self.env["federation.competition.edition"].create({
            "name": "Comp 2025-2026",
            "competition_id": comp.id,
            "season_id": self.season.id,
        })
        comp._compute_edition_count()
        self.assertEqual(comp.edition_count, 1)

    def test_create_edition(self):
        """Test creating a competition edition."""
        comp = self.env["federation.competition"].create({
            "name": "League",
            "competition_type": "league",
        })
        edition = self.env["federation.competition.edition"].create({
            "name": "League 2025-2026",
            "competition_id": comp.id,
            "season_id": self.season.id,
        })
        self.assertEqual(edition.competition_id, comp)
        self.assertEqual(edition.season_id, self.season)
        self.assertEqual(edition.state, "draft")
        self.assertEqual(edition.competition_type, "league")

    def test_edition_state_transitions(self):
        """Test edition state transitions."""
        comp = self.env["federation.competition"].create({
            "name": "Cup",
            "competition_type": "cup",
        })
        edition = self.env["federation.competition.edition"].create({
            "name": "Cup 2025-2026",
            "competition_id": comp.id,
            "season_id": self.season.id,
        })
        self.assertEqual(edition.state, "draft")
        edition.action_open()
        self.assertEqual(edition.state, "open")
        edition.action_start()
        self.assertEqual(edition.state, "in_progress")
        edition.action_close()
        self.assertEqual(edition.state, "closed")

    def test_edition_tournament_link(self):
        """Test linking tournaments (divisions) to an edition."""
        comp = self.env["federation.competition"].create({
            "name": "League",
            "competition_type": "league",
        })
        edition = self.env["federation.competition.edition"].create({
            "name": "League 2025-2026",
            "competition_id": comp.id,
            "season_id": self.season.id,
        })
        tournament = self.env["federation.tournament"].create({
            "name": "Division 1",
            "date_start": "2025-09-01",
            "edition_id": edition.id,
            "competition_id": comp.id,
        })
        edition._compute_tournament_count()
        self.assertEqual(edition.tournament_count, 1)
        self.assertEqual(tournament.edition_id, edition)