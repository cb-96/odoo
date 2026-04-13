from urllib.parse import parse_qs, urlparse

from odoo.tests.common import HttpCase, tagged


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