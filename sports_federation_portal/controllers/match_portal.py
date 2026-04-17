from odoo import fields, http
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.exceptions import AccessError, ValidationError
from odoo.http import request

from .roster_helpers import FederationRosterPortalBase


class FederationMatchPortal(FederationRosterPortalBase):
    """Match sheet and match-day portal routes."""

    @http.route(
        ["/my/match-sheets", "/my/match-sheets/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_match_sheets(self, page=1, **kw):
        """List match sheets visible to the current portal user."""
        MatchSheet = request.env["federation.match.sheet"].with_user(request.env.user).sudo()
        domain = MatchSheet._portal_get_domain(user=request.env.user)
        if domain == [("id", "=", False)]:
            return self._redirect_with_query("/my/club")

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
        """Render a single match sheet."""
        sheet = request.env["federation.match.sheet"].sudo().browse(sheet_id)
        if not sheet.exists():
            return request.not_found()
        try:
            sheet._portal_assert_review_access(user=request.env.user)
        except AccessError:
            return request.not_found()

        values = {
            "sheet": sheet,
            "page_name": "my_match_sheets",
            "success": kw.get("success"),
            "error": kw.get("error"),
            "can_prepare_sheet": sheet.state != "locked",
        }
        return request.render(
            "sports_federation_portal.portal_my_match_sheet_detail",
            values,
        )

    @http.route(
        ["/my/match-sheets/<int:sheet_id>/prep"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_my_match_sheet_prepare(self, sheet_id, **kw):
        """Save match-sheet preparation data."""
        sheet = request.env["federation.match.sheet"].sudo().browse(sheet_id)
        if not sheet.exists():
            return request.not_found()

        try:
            sheet._portal_update_preparation(
                user=request.env.user,
                values={
                    "coach_name": kw.get("coach_name"),
                    "manager_name": kw.get("manager_name"),
                    "notes": kw.get("notes"),
                },
            )
            if kw.get("submit_sheet"):
                sheet._portal_action_submit(user=request.env.user)
        except AccessError:
            return request.not_found()
        except ValidationError as exc:
            return self._redirect_with_query(
                f"/my/match-sheets/{sheet_id}",
                error=str(exc),
            )

        success_message = (
            "Match-day preparation saved and sheet submitted."
            if kw.get("submit_sheet")
            else "Match-day preparation saved."
        )
        return self._redirect_with_query(
            f"/my/match-sheets/{sheet_id}",
            success=success_message,
        )

    @http.route(
        ["/my/match-day", "/my/match-day/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_match_day(self, page=1, **kw):
        """List upcoming match-day sheets for the current user."""
        MatchSheet = request.env["federation.match.sheet"].with_user(request.env.user).sudo()
        domain = MatchSheet._portal_get_domain(user=request.env.user)
        if domain == [("id", "=", False)]:
            return self._redirect_with_query("/my/club")

        domain += [("match_kickoff", "!=", False)]
        total = MatchSheet.search_count(domain)
        pager = portal_pager(
            url="/my/match-day",
            total=total,
            page=page,
            step=20,
        )
        match_day_sheets = MatchSheet.search(
            domain,
            limit=20,
            offset=pager["offset"],
            order="match_kickoff asc, id asc",
        )
        values = {
            "match_day_sheets": match_day_sheets,
            "pager": pager,
            "page_name": "my_match_day",
            "today": fields.Date.context_today(request.env["federation.match.sheet"]),
        }
        return request.render(
            "sports_federation_portal.portal_my_match_day",
            values,
        )