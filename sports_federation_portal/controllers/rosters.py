from urllib.parse import quote_plus

from odoo import fields, http
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.exceptions import AccessError, ValidationError
from odoo.http import request

from .main import FederationPortal


class FederationRosterPortal(FederationPortal):
    def _get_portal_roster(self, roster_id):
        """Return portal roster."""
        Roster = request.env["federation.team.roster"]
        roster = (
            Roster
            .with_user(request.env.user)
            .sudo()
            .browse(roster_id)
        )
        if not roster.exists() or not Roster.with_user(request.env.user).sudo().search_count(
            Roster._portal_get_scope_domain(user=request.env.user) + [("id", "=", roster.id)]
        ):
            raise AccessError("Roster not found")
        return roster

    def _get_portal_roster_line(self, roster, line_id):
        """Return portal roster line."""
        line = (
            request.env["federation.team.roster.line"]
            .with_user(request.env.user)
            .sudo()
            .browse(line_id)
        )
        if not line.exists() or line.roster_id != roster:
            raise AccessError("Roster line not found")
        return line

    def _redirect_roster(self, roster, success=None, error=None):
        """Handle redirect roster."""
        url = f"/my/rosters/{roster.id}"
        if success:
            return request.redirect(f"{url}?success={quote_plus(success)}")
        if error:
            return request.redirect(f"{url}?error={quote_plus(error)}")
        return request.redirect(url)

    @http.route(
        ["/my/rosters", "/my/rosters/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_rosters(self, page=1, **kw):
        """Handle the portal my rosters flow."""
        Roster = request.env["federation.team.roster"].with_user(request.env.user).sudo()
        domain = Roster._portal_get_scope_domain(user=request.env.user)
        if domain == [("id", "=", False)]:
            return request.redirect("/my/club")

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
        confirmed_registrations = request.env[
            "federation.team.roster"
        ]._portal_get_confirmed_registrations(user=request.env.user)
        roster_opportunities = [
            {
                "registration": registration,
                "roster": request.env[
                    "federation.team.roster"
                ]._portal_get_primary_roster_for_registration(
                    registration, user=request.env.user
                ),
            }
            for registration in confirmed_registrations
        ]
        values = {
            "rosters": rosters,
            "roster_opportunities": roster_opportunities,
            "pager": pager,
            "page_name": "my_rosters",
            "success": kw.get("success"),
            "error": kw.get("error"),
        }
        return request.render("sports_federation_portal.portal_my_rosters", values)

    @http.route(
        ["/my/rosters/create/<int:registration_id>"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_my_roster_create(self, registration_id, **kw):
        """Handle the portal my roster create flow."""
        registration = (
            request.env["federation.season.registration"]
            .with_user(request.env.user)
            .sudo()
            .browse(registration_id)
        )
        if not registration.exists():
            return request.redirect(
                "/my/rosters?error=Season+registration+not+found"
            )
        try:
            roster = request.env[
                "federation.team.roster"
            ]._portal_create_roster_for_registration(
                registration, user=request.env.user
            )
        except (AccessError, ValidationError) as exc:
            return request.redirect(
                "/my/rosters?error=%s" % quote_plus(str(exc))
            )
        return self._redirect_roster(
            roster, success="Roster ready for editing in the portal."
        )

    @http.route(
        ["/my/rosters/<int:roster_id>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_roster_detail(self, roster_id, **kw):
        """Handle the portal my roster detail flow."""
        try:
            roster = self._get_portal_roster(roster_id)
        except AccessError:
            return request.not_found()

        can_manage_roster = False
        portal_manage_error = False
        try:
            roster._portal_assert_manage_access(user=request.env.user)
            can_manage_roster = True
        except ValidationError as exc:
            portal_manage_error = str(exc)

        values = {
            "roster": roster,
            "page_name": "my_rosters",
            "success": kw.get("success"),
            "error": kw.get("error"),
            "can_manage_roster": can_manage_roster,
            "can_edit_roster": can_manage_roster and roster.status != "closed",
            "portal_manage_error": portal_manage_error,
        }
        return request.render(
            "sports_federation_portal.portal_my_roster_detail",
            values,
        )

    @http.route(
        ["/my/rosters/<int:roster_id>/edit"],
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
    )
    def portal_my_roster_edit(self, roster_id, **kw):
        """Handle the portal my roster edit flow."""
        try:
            roster = self._get_portal_roster(roster_id)
            roster._portal_assert_manage_access(user=request.env.user)
        except AccessError:
            return request.not_found()
        except ValidationError as exc:
            return self._redirect_roster(roster, error=str(exc))

        values = {
            "roster": roster,
            "page_name": "my_rosters",
            "error": kw.get("error"),
        }
        return request.render(
            "sports_federation_portal.portal_my_roster_edit",
            values,
        )

    @http.route(
        ["/my/rosters/<int:roster_id>/edit"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_my_roster_update(self, roster_id, **kw):
        """Handle the portal my roster update flow."""
        try:
            roster = self._get_portal_roster(roster_id)
            roster._portal_update_roster(
                user=request.env.user,
                values={
                    "name": kw.get("name"),
                    "valid_from": kw.get("valid_from"),
                    "valid_to": kw.get("valid_to"),
                    "notes": kw.get("notes"),
                },
            )
        except AccessError:
            return request.not_found()
        except ValidationError as exc:
            return request.redirect(
                "/my/rosters/%s/edit?error=%s"
                % (roster_id, quote_plus(str(exc)))
            )
        return self._redirect_roster(roster, success="Roster updated.")

    @http.route(
        ["/my/rosters/<int:roster_id>/activate"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_my_roster_activate(self, roster_id, **kw):
        """Handle the portal my roster activate flow."""
        try:
            roster = self._get_portal_roster(roster_id)
            roster._portal_action_activate(user=request.env.user)
        except AccessError:
            return request.not_found()
        except ValidationError as exc:
            return self._redirect_roster(roster, error=str(exc))
        return self._redirect_roster(roster, success="Roster activated.")

    @http.route(
        ["/my/rosters/<int:roster_id>/draft"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_my_roster_set_draft(self, roster_id, **kw):
        """Handle the portal my roster set draft flow."""
        try:
            roster = self._get_portal_roster(roster_id)
            roster._portal_action_set_draft(user=request.env.user)
        except AccessError:
            return request.not_found()
        except ValidationError as exc:
            return self._redirect_roster(roster, error=str(exc))
        return self._redirect_roster(roster, success="Roster set back to draft.")

    @http.route(
        ["/my/rosters/<int:roster_id>/close"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_my_roster_close(self, roster_id, **kw):
        """Handle the portal my roster close flow."""
        try:
            roster = self._get_portal_roster(roster_id)
            roster._portal_action_close(user=request.env.user)
        except AccessError:
            return request.not_found()
        except ValidationError as exc:
            return self._redirect_roster(roster, error=str(exc))
        return self._redirect_roster(roster, success="Roster closed.")

    @http.route(
        ["/my/rosters/<int:roster_id>/lines/new"],
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
    )
    def portal_my_roster_line_new(self, roster_id, **kw):
        """Handle the portal my roster line new flow."""
        try:
            roster = self._get_portal_roster(roster_id)
            roster._portal_assert_manage_access(user=request.env.user)
            line_model = request.env["federation.team.roster.line"]
            available_players = line_model._portal_get_available_players(
                roster, user=request.env.user
            )
            available_licenses = line_model._portal_get_available_licenses(
                roster, user=request.env.user
            )
        except AccessError:
            return request.not_found()
        except ValidationError as exc:
            return self._redirect_roster(roster, error=str(exc))

        values = {
            "roster": roster,
            "line": False,
            "available_players": available_players,
            "available_licenses": available_licenses,
            "submit_url": f"/my/rosters/{roster.id}/lines/new",
            "page_title": "Add Roster Player",
            "page_name": "my_rosters",
            "error": kw.get("error"),
        }
        return request.render(
            "sports_federation_portal.portal_my_roster_line_form",
            values,
        )

    @http.route(
        ["/my/rosters/<int:roster_id>/lines/new"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_my_roster_line_create(self, roster_id, **kw):
        """Handle the portal my roster line create flow."""
        try:
            roster = self._get_portal_roster(roster_id)
            request.env["federation.team.roster.line"]._portal_create_line(
                roster,
                values=kw,
                user=request.env.user,
            )
        except AccessError:
            return request.not_found()
        except ValidationError as exc:
            return request.redirect(
                "/my/rosters/%s/lines/new?error=%s"
                % (roster_id, quote_plus(str(exc)))
            )
        return self._redirect_roster(roster, success="Player added to roster.")

    @http.route(
        ["/my/rosters/<int:roster_id>/lines/<int:line_id>/edit"],
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
    )
    def portal_my_roster_line_edit(self, roster_id, line_id, **kw):
        """Handle the portal my roster line edit flow."""
        try:
            roster = self._get_portal_roster(roster_id)
            line = self._get_portal_roster_line(roster, line_id)
            roster._portal_assert_manage_access(user=request.env.user)
            if line.status != "active":
                return self._redirect_roster(
                    roster,
                    error="Only active roster lines can be edited in the portal.",
                )
            available_licenses = request.env[
                "federation.team.roster.line"
            ]._portal_get_available_licenses(
                roster,
                user=request.env.user,
                player=line.player_id,
            )
        except AccessError:
            return request.not_found()
        except ValidationError as exc:
            return self._redirect_roster(roster, error=str(exc))

        values = {
            "roster": roster,
            "line": line,
            "available_players": False,
            "available_licenses": available_licenses,
            "submit_url": f"/my/rosters/{roster.id}/lines/{line.id}/edit",
            "page_title": "Edit Roster Player",
            "page_name": "my_rosters",
            "error": kw.get("error"),
        }
        return request.render(
            "sports_federation_portal.portal_my_roster_line_form",
            values,
        )

    @http.route(
        ["/my/rosters/<int:roster_id>/lines/<int:line_id>/edit"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_my_roster_line_update(self, roster_id, line_id, **kw):
        """Handle the portal my roster line update flow."""
        try:
            roster = self._get_portal_roster(roster_id)
            line = self._get_portal_roster_line(roster, line_id)
            line._portal_update_line(values=kw, user=request.env.user)
        except AccessError:
            return request.not_found()
        except ValidationError as exc:
            return request.redirect(
                "/my/rosters/%s/lines/%s/edit?error=%s"
                % (roster_id, line_id, quote_plus(str(exc)))
            )
        return self._redirect_roster(roster, success="Roster line updated.")

    @http.route(
        ["/my/rosters/<int:roster_id>/lines/<int:line_id>/delete"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_my_roster_line_delete(self, roster_id, line_id, **kw):
        """Handle the portal my roster line delete flow."""
        try:
            roster = self._get_portal_roster(roster_id)
            line = self._get_portal_roster_line(roster, line_id)
            line._portal_delete_line(user=request.env.user)
        except AccessError:
            return request.not_found()
        except ValidationError as exc:
            return self._redirect_roster(roster, error=str(exc))
        return self._redirect_roster(roster, success="Roster line removed.")

    @http.route(
        ["/my/match-sheets", "/my/match-sheets/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_match_sheets(self, page=1, **kw):
        """Handle the portal my match sheets flow."""
        MatchSheet = request.env["federation.match.sheet"].with_user(request.env.user).sudo()
        domain = MatchSheet._portal_get_domain(user=request.env.user)
        if domain == [("id", "=", False)]:
            return request.redirect("/my/club")

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
        """Handle the portal my match sheet detail flow."""
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
        """Handle the portal my match sheet prepare flow."""
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
            return request.redirect(
                "/my/match-sheets/%s?error=%s"
                % (sheet_id, quote_plus(str(exc)))
            )
        return request.redirect(
            "/my/match-sheets/%s?success=%s"
            % (
                sheet_id,
                quote_plus(
                    "Match-day preparation saved and sheet submitted."
                    if kw.get("submit_sheet")
                    else "Match-day preparation saved."
                ),
            )
        )

    @http.route(
        ["/my/match-day", "/my/match-day/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_match_day(self, page=1, **kw):
        """Handle the portal my match day flow."""
        MatchSheet = request.env["federation.match.sheet"].with_user(request.env.user).sudo()
        domain = MatchSheet._portal_get_domain(user=request.env.user)
        if domain == [("id", "=", False)]:
            return request.redirect("/my/club")
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