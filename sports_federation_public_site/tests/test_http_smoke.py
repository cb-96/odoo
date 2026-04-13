from odoo.tests.common import HttpCase, tagged


@tagged("-at_install", "post_install")
class TestPublicSiteHttpSmoke(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.portal_official_group = cls.env.ref(
            "sports_federation_portal.group_federation_portal_official"
        )
        cls.season = cls.env["federation.season"].create(
            {
                "name": "Public Registration Smoke Season",
                "code": "PRSS",
                "date_start": "2026-01-01",
                "date_end": "2026-12-31",
            }
        )
        cls.tournament = cls.env["federation.tournament"].create(
            {
                "name": "Wrong Role Registration Smoke Tournament",
                "code": "WRRST",
                "season_id": cls.season.id,
                "date_start": "2026-06-01",
                "state": "open",
                "website_published": True,
                "public_slug": "wrong-role-registration-smoke",
            }
        )
        cls.official_user = cls.env["res.users"].with_context(
            no_reset_password=True
        ).create(
            {
                "name": "Wrong Role Registration Smoke User",
                "login": "wrong.role.registration@example.com",
                "email": "wrong.role.registration@example.com",
                "group_ids": [(6, 0, [cls.portal_official_group.id])],
            }
        )

    def test_wrong_role_registration_page_shows_guided_feedback(self):
        self.authenticate(self.official_user.login, "ignored")

        response = self.url_open(self.tournament.get_public_register_path())

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.tournament.name, response.text)
        self.assertIn(
            "You are not registered as a club representative. Please contact the federation.",
            response.text,
        )
        self.assertNotIn("Internal Server Error", response.text)