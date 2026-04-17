from urllib.parse import quote_plus

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import ValidationError


class FederationWebsite(http.Controller):
    """Public website controllers for tournament listing and registration."""

    # ------------------------------------------------------------------
    # Public tournament pages
    # ------------------------------------------------------------------

    @http.route(
        ["/tournaments", "/tournaments/page/<int:page>"],
        type="http",
        auth="public",
        website=True,
    )
    def tournaments_list(self, page=1, search="", **kw):
        """Public tournament listing page."""
        domain = [("state", "in", ("open", "in_progress", "closed"))]
        if search:
            domain += [
                "|",
                ("name", "ilike", search),
                ("location", "ilike", search),
            ]
        Tournament = request.env["federation.tournament"]
        total = Tournament.search_count(domain)
        step = 12
        pager = portal_pager(
            url="/tournaments",
            total=total,
            page=page,
            step=step,
            url_args={"search": search},
        )
        tournaments = Tournament.search(
            domain, limit=step, offset=pager["offset"], order="date_start desc"
        )
        values = {
            "tournaments": tournaments,
            "pager": pager,
            "search": search,
        }
        return request.render("sports_federation_portal.tournament_list_page", values)

    @http.route(
        ["/tournament/<int:tournament_id>"],
        type="http",
        auth="public",
        website=True,
    )
    def tournament_detail(self, tournament_id, **kw):
        """Public tournament detail page."""
        Tournament = request.env["federation.tournament"]
        tournament = Tournament.browse(tournament_id)
        if not tournament.exists():
            return request.not_found()
        participants = request.env["federation.tournament.participant"].search(
            [("tournament_id", "=", tournament_id)],
            order="seed, name",
        )
        values = {
            "tournament": tournament,
            "participants": participants,
            "can_register": tournament.state == "open",
        }
        return request.render("sports_federation_portal.tournament_detail_page", values)

    @http.route(
        ["/tournament/<int:tournament_id>/register"],
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
    )
    def tournament_register_form(self, tournament_id, **kw):
        """Show tournament registration form (requires login)."""
        Tournament = request.env["federation.tournament"]
        tournament = Tournament.browse(tournament_id)
        if not tournament.exists() or tournament.state != "open":
            return request.redirect("/tournaments")
        # Get the user's clubs
        clubs = request.env["federation.club.representative"]._get_clubs_for_user()
        if not clubs:
            values = {
                "error": "You are not registered as a club representative. "
                "Please contact the federation.",
                "tournament": tournament,
            }
            return request.render(
                "sports_federation_portal.tournament_register_page", values
            )
        existing = request.env["federation.tournament.registration"].search(
            [
                ("tournament_id", "=", tournament_id),
                ("team_id.club_id", "in", clubs.ids),
                ("state", "!=", "cancelled"),
            ]
        )
        blocked_reason_by_team_id = {
            team.id: "Already registered or currently awaiting review."
            for team in existing.mapped("team_id")
        }
        selection_snapshot = tournament.get_team_selection_snapshot(
            extra_domain=[("club_id", "in", clubs.ids)],
            blocked_reason_by_team_id=blocked_reason_by_team_id,
        )
        values = {
            "tournament": tournament,
            "clubs": clubs,
            "teams": selection_snapshot["available_teams"],
            "excluded_teams": [
                {
                    "name": item["team"].name,
                    "club": item["team"].club_id.name,
                    "reason": item["reason"],
                }
                for item in selection_snapshot["excluded_teams"]
            ],
            "error": kw.get("error"),
            "success": kw.get("success"),
        }
        return request.render(
            "sports_federation_portal.tournament_register_page", values
        )

    @http.route(
        ["/tournament/<int:tournament_id>/register"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def tournament_register_submit(self, tournament_id, team_id, notes="", **kw):
        """Process tournament registration form submission."""
        Tournament = request.env["federation.tournament"]
        tournament = Tournament.browse(tournament_id)
        if not tournament.exists() or tournament.state != "open":
            return request.redirect("/tournaments")
        try:
            team_id = int(team_id)
        except (ValueError, TypeError):
            return request.redirect(
                f"/tournament/{tournament_id}/register?error=Invalid+team+selection"
            )
        # Verify the team belongs to the user's club
        team = request.env["federation.team"].browse(team_id)
        clubs = request.env["federation.club.representative"]._get_clubs_for_user()
        if team.club_id not in clubs:
            return request.redirect(
                f"/tournament/{tournament_id}/register?error=You+can+only+register+your+own+teams"
            )
        eligibility_error = tournament.get_team_eligibility_error(team)
        if eligibility_error:
            return request.redirect(
                f"/tournament/{tournament_id}/register?error={quote_plus(eligibility_error)}"
            )
        # Check for duplicate
        existing = request.env["federation.tournament.registration"].search(
            [
                ("tournament_id", "=", tournament_id),
                ("team_id", "=", team_id),
                ("state", "!=", "cancelled"),
            ],
            limit=1,
        )
        if existing:
            return request.redirect(
                f"/tournament/{tournament_id}/register?error=This+team+is+already+registered"
            )
        # Check max participants
        if tournament.max_participants > 0:
            current_count = request.env["federation.tournament.participant"].search_count(
                [("tournament_id", "=", tournament_id), ("state", "=", "confirmed")]
            )
            pending_count = request.env["federation.tournament.registration"].search_count(
                [("tournament_id", "=", tournament_id), ("state", "=", "submitted")]
            )
            if current_count + pending_count >= tournament.max_participants:
                return request.redirect(
                    f"/tournament/{tournament_id}/register?error=Tournament+is+full"
                )
        # Create the registration
        try:
            registration = request.env["federation.tournament.registration"].create(
                {
                    "tournament_id": tournament_id,
                    "team_id": team_id,
                    "notes": notes,
                    "user_id": request.env.user.id,
                }
            )
            registration.action_submit()
        except ValidationError as e:
            return request.redirect(
                f"/tournament/{tournament_id}/register?error={quote_plus(str(e))}"
            )
        return request.redirect(
            f"/tournament/{tournament_id}/register?success=Registration+submitted+successfully"
        )


class FederationPortal(CustomerPortal):
    """Portal controllers for club representatives."""

    def _prepare_portal_layout_values(self):
        values = super()._prepare_portal_layout_values()
        representative = request.env["federation.club.representative"].search(
            [("user_id", "=", request.env.user.id)], limit=1
        )
        referee = request.env["federation.referee"].with_user(request.env.user)._portal_get_for_user(
            user=request.env.user
        )
        values["federation_representative"] = representative
        values["federation_club"] = representative.club_id if representative else None
        values["federation_referee"] = referee
        return values

    def _get_portal_default_domain(self):
        """Return domain filter for club-owned records."""
        clubs = request.env["federation.club.representative"]._get_clubs_for_user()
        return [("club_id", "in", clubs.ids)]

    # ------------------------------------------------------------------
    # My Club
    # ------------------------------------------------------------------

    @http.route(
        ["/my/club"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_club(self, **kw):
        """Show the portal user's club information."""
        clubs = request.env["federation.club.representative"]._get_clubs_for_user()
        if not clubs:
            values = {
                "error": "You are not assigned as a club representative. "
                "Please contact the federation.",
            }
            return request.render("sports_federation_portal.portal_my_club", values)
        club = clubs[0]
        teams = request.env["federation.team"].search(
            [("club_id", "=", club.id)], order="name"
        )
        values = {
            "club": club,
            "teams": teams,
            "page_name": "my_club",
        }
        return request.render("sports_federation_portal.portal_my_club", values)

    # ------------------------------------------------------------------
    # My Teams
    # ------------------------------------------------------------------

    @http.route(
        ["/my/teams"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_teams(self, **kw):
        """Show the portal user's teams."""
        clubs = request.env["federation.club.representative"]._get_clubs_for_user()
        if not clubs:
            return request.redirect("/my/club")
        teams = request.env["federation.team"].search(
            [("club_id", "in", clubs.ids)], order="name"
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
        clubs = request.env["federation.club.representative"]._get_clubs_for_user()
        if not clubs:
            return request.redirect("/my/club")
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
        clubs = request.env["federation.club.representative"]._get_clubs_for_user()
        team_name = (name or "").strip()
        category = (category or "").strip()
        gender = (gender or "").strip()
        if not team_name:
            return request.redirect("/my/teams/new?error=Team+name+is+required")
        if not category:
            return request.redirect("/my/teams/new?error=Team+category+is+required")
        if not gender:
            return request.redirect("/my/teams/new?error=Team+gender+is+required")
        try:
            club_id = int(club_id)
        except (ValueError, TypeError):
            return request.redirect("/my/teams/new?error=Invalid+club+selection")
        club = request.env["federation.club"].browse(club_id)
        if club not in clubs:
            return request.redirect("/my/teams?error=You+can+only+create+teams+for+your+own+club")
        try:
            request.env["federation.team"].create({
                "name": team_name,
                "club_id": club.id,
                "category": category,
                "gender": gender,
                "email": email.strip() if email else False,
                "phone": phone.strip() if phone else False,
            })
        except Exception as e:
            return request.redirect("/my/teams/new?error=%s" % (quote_plus(str(e)),))
        return request.redirect("/my/teams?success=Team+created+successfully")

    # ------------------------------------------------------------------
    # My Season Registrations
    # ------------------------------------------------------------------

    @http.route(
        ["/my/season-registrations", "/my/season-registrations/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_season_registrations(self, page=1, **kw):
        """Show season registrations for the user's club."""
        clubs = request.env["federation.club.representative"]._get_clubs_for_user()
        if not clubs:
            return request.redirect("/my/club")
        domain = [("club_id", "in", clubs.ids)]
        Registration = request.env["federation.season.registration"]
        total = Registration.search_count(domain)
        step = 20
        pager = portal_pager(
            url="/my/season-registrations",
            total=total,
            page=page,
            step=step,
        )
        registrations = Registration.search(
            domain, limit=step, offset=pager["offset"], order="create_date desc"
        )
        values = {
            "registrations": registrations,
            "pager": pager,
            "page_name": "my_season_registrations",
            "success": kw.get("success"),
            "error": kw.get("error"),
        }
        return request.render(
            "sports_federation_portal.portal_my_season_registrations", values
        )

    # ------------------------------------------------------------------
    # My Tournament Registrations
    # ------------------------------------------------------------------

    @http.route(
        ["/my/tournament-registrations", "/my/tournament-registrations/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_tournament_registrations(self, page=1, **kw):
        """Show tournament registrations for the user's club."""
        clubs = request.env["federation.club.representative"]._get_clubs_for_user()
        if not clubs:
            return request.redirect("/my/club")
        domain = [("club_id", "in", clubs.ids)]
        Registration = request.env["federation.tournament.registration"]
        total = Registration.search_count(domain)
        step = 20
        pager = portal_pager(
            url="/my/tournament-registrations",
            total=total,
            page=page,
            step=step,
        )
        registrations = Registration.search(
            domain, limit=step, offset=pager["offset"], order="create_date desc"
        )
        values = {
            "registrations": registrations,
            "pager": pager,
            "page_name": "my_tournament_registrations",
        }
        return request.render(
            "sports_federation_portal.portal_my_tournament_registrations", values
        )

    # ------------------------------------------------------------------
    # Active Tournament Workspace
    # ------------------------------------------------------------------

    @http.route(
        ["/my/tournament-workspaces", "/my/tournament-workspaces/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_tournament_workspaces(self, page=1, **kw):
        Tournament = request.env["federation.tournament"]
        entries = Tournament._portal_get_workspace_entries(user=request.env.user)
        step = 12
        pager = portal_pager(
            url="/my/tournament-workspaces",
            total=len(entries),
            page=page,
            step=step,
        )
        values = {
            "workspace_entries": entries[pager["offset"]:pager["offset"] + step],
            "pager": pager,
            "page_name": "my_tournament_workspaces",
            "has_workspace_access": Tournament._portal_has_workspace_access(
                user=request.env.user
            ),
        }
        return request.render(
            "sports_federation_portal.portal_my_tournament_workspaces",
            values,
        )

    @http.route(
        ["/my/tournament-workspaces/<int:tournament_id>/<int:team_id>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_tournament_workspace_detail(self, tournament_id, team_id, **kw):
        workspace_entry = request.env[
            "federation.tournament"
        ]._portal_get_workspace_entry_for_user(
            tournament_id,
            team_id,
            user=request.env.user,
        )
        if not workspace_entry:
            return request.not_found()

        values = {
            "workspace": workspace_entry,
            "page_name": "my_tournament_workspaces",
        }
        return request.render(
            "sports_federation_portal.portal_my_tournament_workspace_detail",
            values,
        )

    # ------------------------------------------------------------------
    # Season registration form
    # ------------------------------------------------------------------

    @http.route(
        ["/my/season-registration/new"],
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
    )
    def portal_season_registration_form(self, **kw):
        """Show season registration form."""
        clubs = request.env["federation.club.representative"]._get_clubs_for_user()
        if not clubs:
            return request.redirect("/my/club")
        teams = request.env["federation.team"].search(
            [("club_id", "in", clubs.ids)], order="name"
        )
        seasons = request.env["federation.season"].search(
            [("state", "=", "open")], order="date_start desc"
        )
        values = {
            "teams": teams,
            "seasons": seasons,
            "page_name": "new_season_registration",
            "error": kw.get("error"),
        }
        return request.render(
            "sports_federation_portal.portal_season_registration_form", values
        )

    @http.route(
        ["/my/season-registration/new"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_season_registration_submit(self, team_id, season_id, notes="", **kw):
        """Submit a season registration."""
        clubs = request.env["federation.club.representative"]._get_clubs_for_user()
        try:
            team_id = int(team_id)
            season_id = int(season_id)
        except (ValueError, TypeError):
            return request.redirect(
                "/my/season-registration/new?error=Invalid+selection"
            )
        team = request.env["federation.team"].browse(team_id)
        season = request.env["federation.season"].browse(season_id)
        if not season.exists() or season.state != "open":
            return request.redirect(
                "/my/season-registration/new?error=The+selected+season+is+not+open+for+registrations"
            )
        if team.club_id not in clubs:
            return request.redirect(
                "/my/season-registration/new?error=You+can+only+register+your+own+teams"
            )
        # Check for duplicate
        existing = request.env["federation.season.registration"].search(
            [
                ("team_id", "=", team_id),
                ("season_id", "=", season_id),
                ("state", "!=", "cancelled"),
            ],
            limit=1,
        )
        if existing:
            return request.redirect(
                "/my/season-registration/new?error=This+team+is+already+registered+for+this+season"
            )
        try:
            registration = request.env["federation.season.registration"].create(
                {
                    "season_id": season_id,
                    "team_id": team_id,
                    "notes": notes,
                    "user_id": request.env.user.id,
                }
            )
            registration.action_submit()
        except ValidationError as e:
            return request.redirect(f"/my/season-registration/new?error={str(e)}")
        return request.redirect(
            "/my/season-registrations?success=Season+registration+submitted"
        )

    # ------------------------------------------------------------------
    # Cancel tournament registration
    # ------------------------------------------------------------------

    @http.route(
        ["/my/tournament-registration/<int:reg_id>/cancel"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_tournament_registration_cancel(self, reg_id, **kw):
        """Cancel a tournament registration."""
        clubs = request.env["federation.club.representative"]._get_clubs_for_user()
        registration = request.env["federation.tournament.registration"].browse(
            reg_id
        )
        if not registration.exists() or registration.club_id not in clubs:
            return request.redirect(
                "/my/tournament-registrations?error=Registration+not+found"
            )
        try:
            registration.action_cancel()
        except ValidationError as e:
            return request.redirect(
                f"/my/tournament-registrations?error={str(e)}"
            )
        return request.redirect(
            "/my/tournament-registrations?success=Registration+cancelled"
        )

    # ------------------------------------------------------------------
    # Cancel season registration
    # ------------------------------------------------------------------

    @http.route(
        ["/my/season-registration/<int:reg_id>/cancel"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_season_registration_cancel(self, reg_id, **kw):
        """Cancel a season registration."""
        clubs = request.env["federation.club.representative"]._get_clubs_for_user()
        registration = request.env["federation.season.registration"].browse(
            reg_id
        )
        if not registration.exists() or registration.club_id not in clubs:
            return request.redirect(
                "/my/season-registrations?error=Registration+not+found"
            )
        try:
            registration.action_cancel()
        except ValidationError as e:
            return request.redirect(
                f"/my/season-registrations?error={str(e)}"
            )
        return request.redirect(
            "/my/season-registrations?success=Registration+cancelled"
        )