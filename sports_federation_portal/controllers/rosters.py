from odoo import http
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.http import request

from .main import FederationPortal


class FederationRosterPortal(FederationPortal):
    @http.route(
        ["/my/rosters", "/my/rosters/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_rosters(self, page=1, **kw):
        clubs = request.env["federation.club.representative"]._get_clubs_for_user()
        if not clubs:
            return request.redirect("/my/club")

        domain = [("club_id", "in", clubs.ids)]
        Roster = request.env["federation.team.roster"].sudo()
        total = Roster.search_count(domain)
        pager = portal_pager(
            url="/my/rosters",
            total=total,
            page=page,
            step=20,
        )
        rosters = Roster.search(
            domain,
            limit=20,
            offset=pager["offset"],
            order="season_id desc, team_id, id desc",
        )
        values = {
            "rosters": rosters,
            "pager": pager,
            "page_name": "my_rosters",
        }
        return request.render("sports_federation_portal.portal_my_rosters", values)

    @http.route(
        ["/my/rosters/<int:roster_id>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_roster_detail(self, roster_id, **kw):
        clubs = request.env["federation.club.representative"]._get_clubs_for_user()
        roster = request.env["federation.team.roster"].sudo().browse(roster_id)
        if not roster.exists() or roster.club_id not in clubs:
            return request.not_found()

        values = {
            "roster": roster,
            "page_name": "my_rosters",
        }
        return request.render(
            "sports_federation_portal.portal_my_roster_detail",
            values,
        )

    @http.route(
        ["/my/match-sheets", "/my/match-sheets/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_match_sheets(self, page=1, **kw):
        clubs = request.env["federation.club.representative"]._get_clubs_for_user()
        if not clubs:
            return request.redirect("/my/club")

        domain = [("team_id.club_id", "in", clubs.ids)]
        MatchSheet = request.env["federation.match.sheet"].sudo()
        total = MatchSheet.search_count(domain)
        pager = portal_pager(
            url="/my/match-sheets",
            total=total,
            page=page,
            step=20,
        )
        match_sheets = MatchSheet.search(
            domain,
            limit=20,
            offset=pager["offset"],
            order="match_id desc, id desc",
        )
        values = {
            "match_sheets": match_sheets,
            "pager": pager,
            "page_name": "my_match_sheets",
        }
        return request.render(
            "sports_federation_portal.portal_my_match_sheets",
            values,
        )

    @http.route(
        ["/my/match-sheets/<int:sheet_id>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_match_sheet_detail(self, sheet_id, **kw):
        clubs = request.env["federation.club.representative"]._get_clubs_for_user()
        sheet = request.env["federation.match.sheet"].sudo().browse(sheet_id)
        if not sheet.exists() or sheet.team_id.club_id not in clubs:
            return request.not_found()

        values = {
            "sheet": sheet,
            "page_name": "my_match_sheets",
        }
        return request.render(
            "sports_federation_portal.portal_my_match_sheet_detail",
            values,
        )