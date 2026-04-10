from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestRosterPortalAccess(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_group = cls.env.ref(
            "sports_federation_portal.group_federation_portal_club"
        )
        cls.role_type = cls.env.ref(
            "sports_federation_portal.role_type_competition_contact"
        )
        cls.season = cls.env["federation.season"].create({
            "name": "Portal Roster Season",
            "code": "PRS2",
            "date_start": "2025-01-01",
            "date_end": "2025-12-31",
        })
        cls.club_a = cls.env["federation.club"].create({
            "name": "Portal Roster Club A",
            "code": "PRCA",
        })
        cls.club_b = cls.env["federation.club"].create({
            "name": "Portal Roster Club B",
            "code": "PRCB",
        })
        cls.team_a = cls.env["federation.team"].create({
            "name": "Portal Roster Team A",
            "club_id": cls.club_a.id,
            "code": "PRTA",
        })
        cls.team_b = cls.env["federation.team"].create({
            "name": "Portal Roster Team B",
            "club_id": cls.club_b.id,
            "code": "PRTB",
        })
        cls.user_a = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Portal Roster User A",
            "login": "portal.roster.a@example.com",
            "email": "portal.roster.a@example.com",
            "groups_id": [(6, 0, [cls.portal_group.id])],
        })
        cls.user_b = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Portal Roster User B",
            "login": "portal.roster.b@example.com",
            "email": "portal.roster.b@example.com",
            "groups_id": [(6, 0, [cls.portal_group.id])],
        })
        cls.env["federation.club.representative"].create({
            "club_id": cls.club_a.id,
            "partner_id": cls.user_a.partner_id.id,
            "user_id": cls.user_a.id,
            "role_type_id": cls.role_type.id,
        })
        cls.env["federation.club.representative"].create({
            "club_id": cls.club_b.id,
            "partner_id": cls.user_b.partner_id.id,
            "user_id": cls.user_b.id,
            "role_type_id": cls.role_type.id,
        })

        cls.player_a = cls.env["federation.player"].create({
            "first_name": "Portal",
            "last_name": "Roster A",
            "gender": "male",
        })
        cls.player_b = cls.env["federation.player"].create({
            "first_name": "Portal",
            "last_name": "Roster B",
            "gender": "male",
        })

        cls.roster_a = cls.env["federation.team.roster"].create({
            "name": "Portal Roster A",
            "team_id": cls.team_a.id,
            "season_id": cls.season.id,
        })
        cls.roster_b = cls.env["federation.team.roster"].create({
            "name": "Portal Roster B",
            "team_id": cls.team_b.id,
            "season_id": cls.season.id,
        })
        cls.env["federation.team.roster.line"].create({
            "roster_id": cls.roster_a.id,
            "player_id": cls.player_a.id,
        })
        cls.env["federation.team.roster.line"].create({
            "roster_id": cls.roster_b.id,
            "player_id": cls.player_b.id,
        })
        cls.roster_a.action_activate()
        cls.roster_b.action_activate()

        cls.tournament = cls.env["federation.tournament"].create({
            "name": "Portal Roster Tournament",
            "code": "PRT2",
            "season_id": cls.season.id,
            "date_start": "2025-06-01",
        })
        cls.match = cls.env["federation.match"].create({
            "tournament_id": cls.tournament.id,
            "home_team_id": cls.team_a.id,
            "away_team_id": cls.team_b.id,
            "date_scheduled": "2025-06-12 18:00:00",
        })
        cls.sheet_a = cls.env["federation.match.sheet"].create({
            "name": "Portal Sheet A",
            "match_id": cls.match.id,
            "team_id": cls.team_a.id,
            "roster_id": cls.roster_a.id,
            "side": "home",
        })
        cls.sheet_b = cls.env["federation.match.sheet"].create({
            "name": "Portal Sheet B",
            "match_id": cls.match.id,
            "team_id": cls.team_b.id,
            "roster_id": cls.roster_b.id,
            "side": "away",
        })

    def test_portal_user_only_sees_own_rosters_match_sheets_and_audit(self):
        visible_rosters = self.env["federation.team.roster"].with_user(self.user_a).search([])
        self.assertIn(self.roster_a, visible_rosters)
        self.assertNotIn(self.roster_b, visible_rosters)

        visible_sheets = self.env["federation.match.sheet"].with_user(self.user_a).search([])
        self.assertIn(self.sheet_a, visible_sheets)
        self.assertNotIn(self.sheet_b, visible_sheets)

        visible_audits = self.env["federation.participation.audit"].with_user(self.user_a).search([])
        self.assertTrue(visible_audits)
        self.assertTrue(all(event.team_id.club_id == self.club_a for event in visible_audits))

    def test_portal_user_cannot_modify_roster_records(self):
        with self.assertRaises(AccessError):
            self.roster_a.with_user(self.user_a).write({"notes": "Not allowed"})
        with self.assertRaises(AccessError):
            self.sheet_a.with_user(self.user_a).write({"notes": "Not allowed"})