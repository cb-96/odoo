from odoo import http
from odoo.exceptions import AccessError, ValidationError
from odoo.http import request

from .portal_helpers import FederationPortalBase


class FederationClubPortal(FederationPortalBase):
    """Club and team portal routes."""

    @http.route(
        ["/my/club"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_club(self, **kw):
        """Show the portal user's club information."""
        clubs = self._get_portal_clubs()
        if not clubs:
            return self._render_unassigned_club()

        club = clubs[0]
        teams = request.env["federation.team"].sudo().search(
            [("club_id", "=", club.id)],
            order="name",
        )
        values = {
            "club": club,
            "teams": teams,
            "page_name": "my_club",
        }
        return request.render("sports_federation_portal.portal_my_club", values)

    @http.route(
        ["/my/teams"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_teams(self, **kw):
        """Show the portal user's teams."""
        clubs = self._get_portal_clubs()
        if not clubs:
            return self._redirect_with_query("/my/club")

        teams = request.env["federation.team"].sudo().search(
            [("club_id", "in", clubs.ids)],
            order="name",
        )
        values = {
            "teams": teams,
            "clubs": clubs,
            "page_name": "my_teams",
            "success": kw.get("success"),
            "error": kw.get("error"),
        }
        return request.render("sports_federation_portal.portal_my_teams", values)

    @http.route(
        ["/my/teams/new"],
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
    )
    def portal_my_teams_new(self, **kw):
        """Render the create-team form."""
        clubs = self._get_portal_clubs()
        if not clubs:
            return self._redirect_with_query("/my/club")

        values = {
            "clubs": clubs,
            "page_name": "new_team",
            "error": kw.get("error"),
        }
        return request.render("sports_federation_portal.portal_my_team_new", values)

    @http.route(
        ["/my/teams/new"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_my_teams_create(self, name, club_id, category=None, gender=None, email=None, phone=None, **kw):
        """Create a team through the portal."""
        try:
            club_id = int(club_id)
        except (ValueError, TypeError):
            return self._redirect_with_query("/my/teams/new", error="Invalid club selection")

        try:
            club = request.env["federation.club"].sudo().browse(club_id)
            request.env["federation.team"]._portal_create_team(
                club,
                values={
                    "name": name,
                    "category": category,
                    "gender": gender,
                    "email": email,
                    "phone": phone,
                },
                user=request.env.user,
            )
        except (AccessError, ValidationError) as error:
            return self._redirect_with_query("/my/teams/new", error=str(error))

        return self._redirect_with_query("/my/teams", success="Team created successfully")