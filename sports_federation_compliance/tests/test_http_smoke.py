from odoo.tests.common import HttpCase, tagged


@tagged("-at_install", "post_install")
class TestComplianceHttpSmoke(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.portal_club_group = cls.env.ref(
            "sports_federation_portal.group_federation_portal_club"
        )
        cls.portal_role_type = cls.env.ref(
            "sports_federation_portal.role_type_competition_contact"
        )
        cls.club = cls.env["federation.club"].create(
            {
                "name": "Compliance Smoke Club",
                "code": "CSC",
            }
        )
        cls.club_user = cls.env["res.users"].with_context(
            no_reset_password=True
        ).create(
            {
                "name": "Compliance Smoke User",
                "login": "compliance.smoke@example.com",
                "email": "compliance.smoke@example.com",
                "group_ids": [(6, 0, [cls.portal_club_group.id])],
            }
        )
        cls.env["federation.club.representative"].create(
            {
                "club_id": cls.club.id,
                "partner_id": cls.club_user.partner_id.id,
                "user_id": cls.club_user.id,
                "role_type_id": cls.portal_role_type.id,
            }
        )
        cls.requirement = cls.env["federation.document.requirement"].create(
            {
                "name": "Compliance Smoke Requirement",
                "code": "CSR",
                "target_model": "federation.club",
                "requires_expiry_date": True,
            }
        )

    def test_compliance_detail_route_supports_dotted_target_models(self):
        entry = self.env["federation.document.requirement"].with_user(
            self.club_user
        )._portal_get_workspace_entry_for_user(
            self.requirement.id,
            "federation.club",
            self.club.id,
            user=self.club_user,
        )

        self.assertTrue(entry)

        self.authenticate(self.club_user.login, "ignored")

        workspace_response = self.url_open("/my/compliance")
        detail_response = self.url_open(entry["detail_url"])

        self.assertEqual(workspace_response.status_code, 200)
        self.assertIn(entry["detail_url"], workspace_response.text)

        self.assertEqual(detail_response.status_code, 200)
        self.assertIn(self.requirement.name, detail_response.text)
        self.assertIn(self.club.name, detail_response.text)
        self.assertIn("No submission is on file yet.", detail_response.text)