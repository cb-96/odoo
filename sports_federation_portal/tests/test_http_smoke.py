import re
from urllib.parse import parse_qs, urlparse

from odoo import SUPERUSER_ID, api
from odoo.tests.common import HttpCase, tagged


def _extract_csrf_token(response_text):
    match = re.search(
        r'name="csrf_token"[^>]*value="([^"]+)"',
        response_text,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        raise AssertionError("CSRF token not found in response")
    return match.group(1)


@tagged("-at_install", "post_install")
class TestPortalHttpSmoke(HttpCase):
    def test_web_login_recovers_from_stale_csrf_submission(self):
        login = "portal.login.smoke@example.com"

        response = self.url_open(
            "/web/login",
            data={
                "login": login,
                "password": "ignored",
                "csrf_token": "stale-token",
            },
            allow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)

        location = urlparse(response.url)
        query = parse_qs(location.query)

        self.assertEqual(location.path, "/web/login")
        self.assertEqual(query.get("session_expired"), ["1"])
        self.assertEqual(query.get("login"), [login])
        self.assertIn(
            "Your session expired. Please sign in again and retry your last action.",
            response.text,
        )
        self.assertIn(login, response.text)


@tagged("-at_install", "post_install")
class TestPortalWorkflowHttpSmoke(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        with cls.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            portal_club_group = env.ref(
                "sports_federation_portal.group_federation_portal_club"
            )
            portal_official_group = env.ref(
                "sports_federation_portal.group_federation_portal_official"
            )
            portal_role_type = env.ref(
                "sports_federation_portal.role_type_competition_contact"
            )

            team_club = env["federation.club"].create(
                {
                    "name": "Portal Team Smoke Club",
                    "code": "PTSC",
                }
            )
            team_user = env["res.users"].with_context(
                no_reset_password=True
            ).create(
                {
                    "name": "Portal Team Smoke User",
                    "login": "portal.team.smoke@example.com",
                    "email": "portal.team.smoke@example.com",
                    "group_ids": [(6, 0, [portal_club_group.id])],
                }
            )
            env["federation.club.representative"].create(
                {
                    "club_id": team_club.id,
                    "partner_id": team_user.partner_id.id,
                    "user_id": team_user.id,
                    "role_type_id": portal_role_type.id,
                }
            )

            season_club = env["federation.club"].create(
                {
                    "name": "Portal Season Smoke Club",
                    "code": "PSSC",
                }
            )
            season_user = env["res.users"].with_context(
                no_reset_password=True
            ).create(
                {
                    "name": "Portal Season Smoke User",
                    "login": "portal.season.smoke@example.com",
                    "email": "portal.season.smoke@example.com",
                    "group_ids": [(6, 0, [portal_club_group.id])],
                }
            )
            env["federation.club.representative"].create(
                {
                    "club_id": season_club.id,
                    "partner_id": season_user.partner_id.id,
                    "user_id": season_user.id,
                    "role_type_id": portal_role_type.id,
                }
            )
            season_team = env["federation.team"].create(
                {
                    "name": "Portal Season Smoke Team",
                    "club_id": season_club.id,
                    "code": "PSST",
                    "category": "senior",
                    "gender": "male",
                }
            )
            open_season = env["federation.season"].create(
                {
                    "name": "Portal Smoke Season",
                    "code": "PSS",
                    "date_start": "2026-01-01",
                    "date_end": "2026-12-31",
                    "state": "open",
                }
            )

            officiating_club = env["federation.club"].create(
                {
                    "name": "Portal Officiating Smoke Club",
                    "code": "POSC",
                }
            )
            home_team = env["federation.team"].create(
                {
                    "name": "Portal Officiating Home",
                    "club_id": officiating_club.id,
                    "code": "POH",
                }
            )
            away_team = env["federation.team"].create(
                {
                    "name": "Portal Officiating Away",
                    "club_id": officiating_club.id,
                    "code": "POA",
                }
            )
            officiating_season = env["federation.season"].create(
                {
                    "name": "Portal Officiating Smoke Season",
                    "code": "POSS",
                    "date_start": "2026-01-01",
                    "date_end": "2026-12-31",
                }
            )
            officiating_tournament = env["federation.tournament"].create(
                {
                    "name": "Portal Officiating Smoke Tournament",
                    "code": "POST",
                    "season_id": officiating_season.id,
                    "date_start": "2026-06-01",
                }
            )
            official_user = env["res.users"].with_context(
                no_reset_password=True
            ).create(
                {
                    "name": "Portal Official Smoke User",
                    "login": "portal.official.smoke@example.com",
                    "email": "portal.official.smoke@example.com",
                    "group_ids": [(6, 0, [portal_official_group.id])],
                }
            )
            referee = env["federation.referee"].create(
                {
                    "name": "Portal Official Smoke Referee",
                    "email": "portal.official.smoke@example.com",
                    "certification_level": "national",
                    "user_id": official_user.id,
                }
            )
            assignment_match = env["federation.match"].create(
                {
                    "tournament_id": officiating_tournament.id,
                    "home_team_id": home_team.id,
                    "away_team_id": away_team.id,
                    "date_scheduled": "2026-06-12 18:00:00",
                }
            )
            assignment = env["federation.match.referee"].create(
                {
                    "match_id": assignment_match.id,
                    "referee_id": referee.id,
                    "role": "head",
                }
            )
            cr.commit()

        cls.portal_club_group = cls.env.ref(
            "sports_federation_portal.group_federation_portal_club"
        )
        cls.portal_official_group = cls.env.ref(
            "sports_federation_portal.group_federation_portal_official"
        )
        cls.portal_role_type = cls.env.ref(
            "sports_federation_portal.role_type_competition_contact"
        )
        cls.team_club = cls.env["federation.club"].browse(team_club.id)
        cls.team_user = cls.env["res.users"].browse(team_user.id)
        cls.season_club = cls.env["federation.club"].browse(season_club.id)
        cls.season_user = cls.env["res.users"].browse(season_user.id)
        cls.season_team = cls.env["federation.team"].browse(season_team.id)
        cls.open_season = cls.env["federation.season"].browse(open_season.id)
        cls.officiating_club = cls.env["federation.club"].browse(officiating_club.id)
        cls.home_team = cls.env["federation.team"].browse(home_team.id)
        cls.away_team = cls.env["federation.team"].browse(away_team.id)
        cls.officiating_season = cls.env["federation.season"].browse(officiating_season.id)
        cls.officiating_tournament = cls.env["federation.tournament"].browse(officiating_tournament.id)
        cls.official_user = cls.env["res.users"].browse(official_user.id)
        cls.referee = cls.env["federation.referee"].browse(referee.id)
        cls.assignment_match = cls.env["federation.match"].browse(assignment_match.id)
        cls.assignment = cls.env["federation.match.referee"].browse(assignment.id)

    def test_my_teams_empty_state_and_create_flow(self):
        self.authenticate(self.team_user.login, "ignored")

        list_response = self.url_open("/my/teams")
        self.assertEqual(list_response.status_code, 200)
        self.assertIn("Create Your First Team", list_response.text)

        form_response = self.url_open("/my/teams/new")
        create_response = self.url_open(
            "/my/teams/new",
            data={
                "csrf_token": _extract_csrf_token(form_response.text),
                "name": "Portal Team Smoke Squad",
                "club_id": str(self.team_club.id),
                "category": "senior",
                "gender": "male",
            },
            allow_redirects=True,
        )

        self.assertEqual(create_response.status_code, 200)
        self.assertIn("Team created successfully", create_response.text)
        self.assertIn("Portal Team Smoke Squad", create_response.text)

    def test_season_registration_submit_flow_renders_success(self):
        self.authenticate(self.season_user.login, "ignored")

        list_response = self.url_open("/my/season-registrations")
        self.assertEqual(list_response.status_code, 200)
        self.assertIn(
            "No season registrations have been submitted yet.",
            list_response.text,
        )

        form_response = self.url_open("/my/season-registration/new")
        submit_response = self.url_open(
            "/my/season-registration/new",
            data={
                "csrf_token": _extract_csrf_token(form_response.text),
                "season_id": str(self.open_season.id),
                "team_id": str(self.season_team.id),
                "notes": "Ready for portal smoke coverage.",
            },
            allow_redirects=True,
        )

        self.assertEqual(submit_response.status_code, 200)
        self.assertIn("Season registration submitted", submit_response.text)
        self.assertIn(self.season_team.name, submit_response.text)
        self.assertNotIn("Internal Server Error", submit_response.text)

    def test_officiating_response_flow_renders_success(self):
        self.authenticate(self.official_user.login, "ignored")

        detail_response = self.url_open(
            f"/my/referee-assignments/{self.assignment.id}"
        )
        submit_response = self.url_open(
            f"/my/referee-assignments/{self.assignment.id}/respond",
            data={
                "csrf_token": _extract_csrf_token(detail_response.text),
                "action": "confirm",
                "response_note": "Confirmed from smoke test.",
            },
            allow_redirects=True,
        )

        self.assertEqual(submit_response.status_code, 200)
        self.assertIn("Assignment confirmed.", submit_response.text)
        self.assertIn("Confirmed from smoke test.", submit_response.text)