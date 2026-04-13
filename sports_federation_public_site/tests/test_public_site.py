from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase


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
        self.assertFalse(self.tournament.can_access_public_detail())

    def test_published_tournament_detail_renders(self):
        """Test that published tournament detail renders."""
        self.tournament.website_published = True
        self.assertTrue(self.tournament.can_access_public_detail())

    def test_results_visibility_requires_results_toggle(self):
        """Direct results access requires both publish and results flags."""
        self.tournament.website_published = True
        self.tournament.show_public_results = False
        self.assertFalse(self.tournament.can_access_public_results())

        self.tournament.show_public_results = True
        self.assertTrue(self.tournament.can_access_public_results())

    def test_public_results_query_only_returns_approved_matches(self):
        approved_match = self.env["federation.match"].create({
            "tournament_id": self.tournament.id,
            "home_team_id": False,
            "away_team_id": False,
            "result_state": "approved",
        })
        submitted_match = self.env["federation.match"].create({
            "tournament_id": self.tournament.id,
            "home_team_id": False,
            "away_team_id": False,
            "result_state": "submitted",
        })

        matches = self.env["federation.match"].search([
            ("tournament_id", "=", self.tournament.id),
            ("result_state", "=", "approved"),
        ])
        self.assertIn(approved_match, matches)
        self.assertNotIn(submitted_match, matches)

    def test_standings_visibility_requires_standings_toggle(self):
        """Direct standings access requires both publish and standings flags."""
        self.tournament.website_published = True
        self.tournament.show_public_standings = False
        self.assertFalse(self.tournament.can_access_public_standings())

        self.tournament.show_public_standings = True
        self.assertTrue(self.tournament.can_access_public_standings())

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
        self.tournament.public_featured = True
        self.tournament.public_editorial_summary = "Front-page summary"
        self.tournament.public_pinned_announcement = "Pinned note"
        self.tournament.show_public_results = True
        self.tournament.show_public_standings = True
        self.assertIn("Test description", str(self.tournament.public_description))
        self.assertEqual(self.tournament.public_slug, "test-slug")
        self.assertTrue(self.tournament.public_featured)
        self.assertEqual(self.tournament.public_editorial_summary, "Front-page summary")
        self.assertEqual(self.tournament.public_pinned_announcement, "Pinned note")
        self.assertTrue(self.tournament.show_public_results)
        self.assertTrue(self.tournament.show_public_standings)

    def test_public_slug_must_be_unique(self):
        self.tournament.public_slug = "shared-slug"
        with self.assertRaises(Exception), self.cr.savepoint():
            self.env["federation.tournament"].create({
                "name": "Other Tournament",
                "code": "OTHER-TT",
                "date_start": "2024-02-01",
                "date_end": "2024-02-28",
                "public_slug": "shared-slug",
            })

    def test_menu_cleanup_rehomes_legacy_competitions_menu(self):
        website = self.env["website"].search([], limit=1)
        root_menu = self.env["website.menu"].create({
            "name": "Top Menu Cleanup Root",
            "url": "#",
            "website_id": website.id,
        })
        tournament_menu = self.env["website.menu"].create({
            "name": "Tournaments",
            "url": "/tournaments",
            "parent_id": root_menu.id,
            "sequence": 50,
            "website_id": website.id,
        })
        legacy_menu = self.env["website.menu"].create({
            "name": "Competitions",
            "url": "/competitions",
            "parent_id": root_menu.id,
            "sequence": 55,
            "is_visible": True,
            "website_id": website.id,
        })

        self.env["website.menu"]._cleanup_stale_public_site_menus()

        legacy_menu = self.env["website.menu"].browse(legacy_menu.id)
        self.assertEqual(legacy_menu.parent_id, tournament_menu)
        self.assertEqual(legacy_menu.name, "Published Coverage")
        self.assertEqual(legacy_menu.url, "/tournaments#published")
        self.assertTrue(legacy_menu.is_visible)
        self.assertEqual(legacy_menu.sequence, 10)

    def test_menu_cleanup_hides_duplicate_legacy_entries(self):
        website = self.env["website"].search([], limit=1)
        root_menu = self.env["website.menu"].create({
            "name": "Top Menu Cleanup Duplicate Root",
            "url": "#",
            "website_id": website.id,
        })
        tournament_menu = self.env["website.menu"].create({
            "name": "Tournaments",
            "url": "/tournaments",
            "parent_id": root_menu.id,
            "sequence": 50,
            "website_id": website.id,
        })
        published_menu = self.env["website.menu"].create({
            "name": "Published Coverage",
            "url": "/tournaments#published",
            "parent_id": tournament_menu.id,
            "sequence": 10,
            "is_visible": True,
            "website_id": website.id,
        })
        legacy_sibling = self.env["website.menu"].create({
            "name": "Competitions",
            "url": "/competitions",
            "parent_id": root_menu.id,
            "sequence": 55,
            "is_visible": True,
            "website_id": website.id,
        })
        legacy_child = self.env["website.menu"].create({
            "name": "Competition Archive",
            "url": "/competitions/archive",
            "parent_id": tournament_menu.id,
            "sequence": 15,
            "is_visible": True,
            "website_id": website.id,
        })

        self.env["website.menu"]._cleanup_stale_public_site_menus()

        published_menu = self.env["website.menu"].browse(published_menu.id)
        self.assertEqual(published_menu.parent_id, tournament_menu)
        self.assertEqual(published_menu.name, "Published Coverage")
        self.assertEqual(published_menu.url, "/tournaments#published")
        self.assertTrue(published_menu.is_visible)
        self.assertFalse(legacy_sibling.exists())
        self.assertFalse(legacy_child.exists())

    def test_standing_public_fields(self):
        """Test that standing public fields are set correctly."""
        self.standing.website_published = True
        self.standing.public_title = "Public Title"
        self.assertEqual(self.standing.public_title, "Public Title")