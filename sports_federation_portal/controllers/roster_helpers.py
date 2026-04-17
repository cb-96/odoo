from odoo.exceptions import AccessError
from odoo.http import request

from .portal_helpers import FederationPortalBase


class FederationRosterPortalBase(FederationPortalBase):
    """Shared helpers for roster and match-day portal routes."""

    def _get_portal_roster(self, roster_id):
        """Return a roster visible to the current portal user."""
        Roster = request.env["federation.team.roster"].with_user(request.env.user).sudo()
        roster = Roster.browse(roster_id)
        if not roster.exists() or not Roster.search_count(
            Roster._portal_get_scope_domain(user=request.env.user) + [("id", "=", roster.id)]
        ):
            raise AccessError("Roster not found")
        return roster

    def _get_portal_roster_line(self, roster, line_id):
        """Return a roster line bound to the given roster."""
        line = request.env["federation.team.roster.line"].with_user(request.env.user).sudo().browse(line_id)
        if not line.exists() or line.roster_id != roster:
            raise AccessError("Roster line not found")
        return line

    def _redirect_roster(self, roster, success=None, error=None):
        """Redirect back to a roster detail page with optional status messages."""
        return self._redirect_with_query(
            f"/my/rosters/{roster.id}",
            success=success,
            error=error,
        )

    def _render_roster_line_form(
        self,
        roster,
        submit_url,
        page_title,
        line=False,
        available_players=False,
        available_licenses=False,
        error=None,
    ):
        """Render the roster line form with shared template values."""
        values = {
            "roster": roster,
            "line": line,
            "available_players": available_players,
            "available_licenses": available_licenses,
            "submit_url": submit_url,
            "page_title": page_title,
            "page_name": "my_rosters",
            "error": error,
        }
        return request.render(
            "sports_federation_portal.portal_my_roster_line_form",
            values,
        )