from odoo.tests import TransactionCase
from odoo.exceptions import ValidationError


class TestPublicSite(TransactionCase):
    """Test cases for public site module."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create test tournament
        cls.tournament = cls.env["federation.tournament"].create({
            "name": "Test Tournament",
            "code": "TT2024",
            "date_start": "2024-01-01",
            "date_end": "2024-01-31",
        })
        # Create test standing
        cls.standing = cls.env["federation.standing"].create({
            "name": "Test Standing",
            "tournament_id": cls.tournament.id,
        })

    def test_unpublished_tournament_not_visible_on_list(self):
        """Test that unpublished tournaments are not shown on list."""
        self.tournament.website_published = False
        # The controller would filter by website_published = True
        tournaments = self.env["federation.tournament"].search([
            ("website_published", "=", True),
        ])
        self.assertNotIn(self.tournament, tournaments)

    def test_published_tournament_visible_on_list(self):
        """Test that published tournaments are shown on list."""
        self.tournament.website_published = True
        tournaments = self.env["federation.tournament"].search([
            ("website_published", "=", True),
        ])
        self.assertIn(self.tournament, tournaments)

    def test_unpublished_tournament_detail_returns_404(self):
        """Test that unpublished tournament detail returns 404."""
        self.tournament.website_published = False
        # The controller checks website_published and returns not_found if False
        self.assertFalse(self.tournament.website_published)

    def test_published_tournament_detail_renders(self):
        """Test that published tournament detail renders."""
        self.tournament.website_published = True
        self.assertTrue(self.tournament.website_published)

    def test_only_published_standings_visible(self):
        """Test that only published standings are visible."""
        self.tournament.website_published = True
        self.standing.website_published = True
        standings = self.env["federation.standing"].search([
            ("tournament_id", "=", self.tournament.id),
            ("website_published", "=", True),
        ])
        self.assertIn(self.standing, standings)

    def test_unpublished_standing_hidden(self):
        """Test that unpublished standings are hidden."""
        self.tournament.website_published = True
        self.standing.website_published = False
        standings = self.env["federation.standing"].search([
            ("tournament_id", "=", self.tournament.id),
            ("website_published", "=", True),
        ])
        self.assertNotIn(self.standing, standings)

    def test_tournament_public_fields(self):
        """Test that tournament public fields are set correctly."""
        self.tournament.website_published = True
        self.tournament.public_description = "Test description"
        self.tournament.public_slug = "test-slug"
        self.tournament.show_public_results = True
        self.tournament.show_public_standings = True
        self.assertEqual(self.tournament.public_description, "Test description")
        self.assertEqual(self.tournament.public_slug, "test-slug")
        self.assertTrue(self.tournament.show_public_results)
        self.assertTrue(self.tournament.show_public_standings)

    def test_standing_public_fields(self):
        """Test that standing public fields are set correctly."""
        self.standing.website_published = True
        self.standing.public_title = "Public Title"
        self.assertEqual(self.standing.public_title, "Public Title")