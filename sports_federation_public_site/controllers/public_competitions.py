import json
from urllib.parse import quote_plus

from odoo import http
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.addons.sports_federation_portal.controllers.main import FederationWebsite
from odoo.exceptions import ValidationError
from odoo.http import Response, request


class PublicTournamentHubController(FederationWebsite):

    def _parse_int_param(self, value):
        try:
            return int(value) if value else False
        except (TypeError, ValueError):
            return False

    def _build_filters(self, search="", **kw):
        return {
            "search": (search or kw.get("search") or "").strip(),
            "season_id": self._parse_int_param(kw.get("season_id")),
            "state": (kw.get("state") or "").strip(),
            "category": (kw.get("category") or "").strip(),
            "gender": (kw.get("gender") or "").strip(),
            "venue_id": self._parse_int_param(kw.get("venue_id")),
        }

    def _build_shared_filter_domain(self, filters):
        Tournament = request.env["federation.tournament"]
        domain = []
        if filters["search"]:
            domain += Tournament._get_public_site_search_domain(filters["search"])
        if filters["season_id"]:
            domain.append(("season_id", "=", filters["season_id"]))
        if filters["category"]:
            domain.append(("category", "=", filters["category"]))
        if filters["gender"]:
            domain.append(("gender", "=", filters["gender"]))
        if filters["venue_id"] and "venue_id" in Tournament._fields:
            domain.append(("venue_id", "=", filters["venue_id"]))
        return domain

    def _build_main_tournament_domain(self, filters):
        domain = [("state", "in", ("open", "in_progress", "closed", "cancelled"))]
        domain += self._build_shared_filter_domain(filters)
        if filters["state"]:
            domain.append(("state", "=", filters["state"]))
        return domain

    def _get_filter_reference_data(self):
        Tournament = request.env["federation.tournament"]
        category_options = [("", "All Categories")] + list(Tournament._fields["category"].selection)
        gender_options = [("", "All Genders")] + list(Tournament._fields["gender"].selection)
        state_options = [
            ("", "All States"),
            ("open", "Open"),
            ("in_progress", "In Progress"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ]
        return {
            "category_options": category_options,
            "gender_options": gender_options,
            "state_options": state_options,
            "seasons": request.env["federation.season"].sudo().search([], order="date_start desc, id desc"),
            "venues": request.env["federation.venue"].sudo().search([], order="name asc") if "venue_id" in Tournament._fields else request.env["federation.venue"].browse([]),
        }

    def _resolve_tournament(self, tournament_slug=None, tournament_id=None, tournament=False):
        Tournament = request.env["federation.tournament"]
        if tournament:
            return tournament.sudo()
        if tournament_id:
            return Tournament.sudo().browse(int(tournament_id))
        if tournament_slug:
            return Tournament.resolve_public_slug(tournament_slug)
        return Tournament.browse([])

    def _resolve_team(self, team_slug):
        return request.env["federation.team"].resolve_public_slug(team_slug)

    def _canonical_redirect(self, record, slug_value, path_getter):
        if slug_value != record.get_public_slug_value():
            return request.redirect(path_getter())
        return None

    @http.route(["/competitions"], type="http", auth="public", website=True)
    def competitions_list(self, **kw):
        return request.redirect("/tournaments#published")

    @http.route(["/competitions/archive"], type="http", auth="public", website=True)
    def competitions_archive(self, **kw):
        return request.redirect("/tournaments?state=closed#published-archive")

    @http.route(["/competitions/api/json", "/tournaments/api/json"], type="jsonrpc", auth="public", methods=["POST"])
    def competitions_api_json(self, **kw):
        tournaments = request.env["federation.tournament"].get_public_published_tournaments(limit=None)
        return {
            "tournaments": [
                {
                    "id": tournament.id,
                    "name": tournament.name,
                    "slug": tournament.get_public_slug_value(),
                    "state": tournament.state,
                    "date_start": tournament.date_start.isoformat() if tournament.date_start else None,
                    "date_end": tournament.date_end.isoformat() if tournament.date_end else None,
                    "url": tournament.get_public_path(),
                    "featured": tournament.public_featured,
                }
                for tournament in tournaments
            ]
        }

    @http.route(["/tournaments", "/tournaments/page/<int:page>"], type="http", auth="public", website=True)
    def tournaments_list(self, page=1, search="", **kw):
        filters = self._build_filters(search=search, **kw)
        Tournament = request.env["federation.tournament"].sudo()

        main_domain = self._build_main_tournament_domain(filters)
        total = Tournament.search_count(main_domain)
        step = 12
        pager = portal_pager(
            url="/tournaments",
            total=total,
            page=page,
            step=step,
            url_args={key: value for key, value in filters.items() if value},
        )
        tournaments = Tournament.search(
            main_domain,
            limit=step,
            offset=pager["offset"],
            order="date_start desc, id desc",
        )

        shared_public_domain = self._build_shared_filter_domain(filters)
        featured_public_domain = list(shared_public_domain)
        if filters["state"]:
            featured_public_domain.append(("state", "=", filters["state"]))

        if filters["state"] and filters["state"] not in ("", "closed", "cancelled"):
            archived_public_tournaments = Tournament.browse([])
        else:
            archive_domain = list(shared_public_domain)
            if filters["state"] in ("closed", "cancelled"):
                archive_domain.append(("state", "=", filters["state"]))
            archived_public_tournaments = Tournament.get_public_archived_tournaments(limit=6, extra_domain=archive_domain)

        live_public_tournaments = (
            Tournament.get_public_live_tournaments(limit=4, extra_domain=shared_public_domain)
            if filters["state"] in ("", "in_progress")
            else Tournament.browse([])
        )
        recent_public_tournaments = (
            Tournament.get_public_recent_result_tournaments(limit=4, extra_domain=shared_public_domain)
            if filters["state"] != "cancelled"
            else Tournament.browse([])
        )

        values = {
            "tournaments": tournaments,
            "pager": pager,
            "filters": filters,
            "featured_public_tournaments": Tournament.get_public_featured_tournaments(limit=6, extra_domain=featured_public_domain),
            "archived_public_tournaments": archived_public_tournaments,
            "live_public_tournaments": live_public_tournaments,
            "recent_public_tournaments": recent_public_tournaments,
            "page_name": "tournaments_hub",
        }
        values.update(self._get_filter_reference_data())
        return request.render("sports_federation_public_site.page_tournaments_hub", values)

    @http.route(["/tournament/<int:tournament_id>/coverage", "/competitions/<model('federation.tournament'):tournament>"], type="http", auth="public", website=True)
    def legacy_public_overview(self, tournament_id=None, tournament=False, **kw):
        tournament = self._resolve_tournament(tournament_id=tournament_id, tournament=tournament)
        if not tournament.exists() or not tournament.can_access_public_detail():
            return request.not_found()
        return request.redirect(tournament.get_public_path())

    @http.route(["/tournaments/<string:tournament_slug>", "/tournament/<int:tournament_id>"], type="http", auth="public", website=True)
    def tournament_detail(self, tournament_slug=None, tournament_id=None, **kw):
        tournament = self._resolve_tournament(tournament_slug=tournament_slug, tournament_id=tournament_id)
        if not tournament.exists():
            return request.not_found()

        if tournament_slug:
            redirect = self._canonical_redirect(tournament, tournament_slug, tournament.get_public_path)
            if redirect:
                return redirect
        else:
            return request.redirect(tournament.get_public_path())

        participants = request.env["federation.tournament.participant"].sudo().search(
            [("tournament_id", "=", tournament.id), ("state", "!=", "withdrawn")],
            order="state asc, seed asc, team_id asc",
        )
        values = {
            "tournament": tournament,
            "participants": participants,
            "can_register": tournament.state == "open",
            "public_live_matches": tournament.get_public_live_matches(limit=4) if tournament.can_access_public_detail() else request.env["federation.match"].browse([]),
            "upcoming_matches": tournament.get_public_upcoming_matches(limit=4) if tournament.can_access_public_detail() else request.env["federation.match"].browse([]),
            "recent_results": tournament.get_public_recent_result_matches(limit=4) if tournament.can_access_public_detail() else request.env["federation.match"].browse([]),
            "public_standings": tournament.get_public_standings() if tournament.can_access_public_detail() else request.env["federation.standing"].browse([]),
            "public_participants": tournament.get_public_participants(limit=12) if tournament.can_access_public_detail() else participants[:12],
            "page_name": "tournament_overview",
        }
        return request.render("sports_federation_public_site.page_tournament_overview", values)

    @http.route(["/tournaments/<string:tournament_slug>/register"], type="http", auth="user", website=True, methods=["GET"])
    def tournament_register_form(self, tournament_slug=None, **kw):
        tournament = self._resolve_tournament(tournament_slug=tournament_slug)
        if not tournament.exists() or tournament.state != "open":
            return request.redirect("/tournaments")

        clubs = request.env["federation.club.representative"]._get_clubs_for_user()
        if not clubs:
            values = {
                "error": "You are not registered as a club representative. Please contact the federation.",
                "tournament": tournament,
            }
            return request.render("sports_federation_public_site.page_tournament_register", values)

        existing = request.env["federation.tournament.registration"].sudo().search(
            [
                ("tournament_id", "=", tournament.id),
                ("team_id.club_id", "in", clubs.ids),
                ("state", "!=", "cancelled"),
            ]
        )
        blocked_reason_by_team_id = {
            team.id: "Already registered or currently awaiting review."
            for team in existing.mapped("team_id")
        }
        selection_snapshot = tournament.sudo().get_team_selection_snapshot(
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
        return request.render("sports_federation_public_site.page_tournament_register", values)

    @http.route(["/tournament/<int:tournament_id>/register"], type="http", auth="user", website=True, methods=["GET"])
    def tournament_register_form_legacy(self, tournament_id, **kw):
        tournament = self._resolve_tournament(tournament_id=tournament_id)
        if not tournament.exists():
            return request.redirect("/tournaments")
        return request.redirect(tournament.get_public_register_path())

    @http.route(["/tournaments/<string:tournament_slug>/register"], type="http", auth="user", website=True, methods=["POST"], csrf=True)
    def tournament_register_submit(self, tournament_slug, team_id, notes="", **kw):
        tournament = self._resolve_tournament(tournament_slug=tournament_slug)
        if not tournament.exists() or tournament.state != "open":
            return request.redirect("/tournaments")

        try:
            team_id = int(team_id)
        except (ValueError, TypeError):
            return request.redirect(f"{tournament.get_public_register_path()}?error=Invalid+team+selection")

        team = request.env["federation.team"].sudo().browse(team_id)
        clubs = request.env["federation.club.representative"]._get_clubs_for_user()
        if team.club_id not in clubs:
            return request.redirect(f"{tournament.get_public_register_path()}?error=You+can+only+register+your+own+teams")

        eligibility_error = tournament.get_team_eligibility_error(team)
        if eligibility_error:
            return request.redirect(f"{tournament.get_public_register_path()}?error={quote_plus(eligibility_error)}")

        existing = request.env["federation.tournament.registration"].sudo().search(
            [
                ("tournament_id", "=", tournament.id),
                ("team_id", "=", team_id),
                ("state", "!=", "cancelled"),
            ],
            limit=1,
        )
        if existing:
            return request.redirect(f"{tournament.get_public_register_path()}?error=This+team+is+already+registered")

        if tournament.max_participants > 0:
            current_count = request.env["federation.tournament.participant"].sudo().search_count(
                [("tournament_id", "=", tournament.id), ("state", "=", "confirmed")]
            )
            pending_count = request.env["federation.tournament.registration"].sudo().search_count(
                [("tournament_id", "=", tournament.id), ("state", "=", "submitted")]
            )
            if current_count + pending_count >= tournament.max_participants:
                return request.redirect(f"{tournament.get_public_register_path()}?error=Tournament+is+full")

        try:
            registration = request.env["federation.tournament.registration"].sudo().create(
                {
                    "tournament_id": tournament.id,
                    "team_id": team_id,
                    "notes": notes,
                    "user_id": request.env.user.id,
                }
            )
            registration.sudo().action_submit()
        except ValidationError as error:
            return request.redirect(f"{tournament.get_public_register_path()}?error={quote_plus(str(error))}")

        return request.redirect(f"{tournament.get_public_register_path()}?success=Registration+submitted+successfully")

    @http.route(["/tournament/<int:tournament_id>/register"], type="http", auth="user", website=True, methods=["POST"], csrf=True)
    def tournament_register_submit_legacy(self, tournament_id, team_id, notes="", **kw):
        tournament = self._resolve_tournament(tournament_id=tournament_id)
        if not tournament.exists():
            return request.redirect("/tournaments")
        return self.tournament_register_submit(tournament.get_public_slug_value(), team_id, notes=notes, **kw)

    @http.route([
        "/tournaments/<string:tournament_slug>/teams",
        "/tournament/<int:tournament_id>/teams",
        "/competitions/<model('federation.tournament'):tournament>/teams",
    ], type="http", auth="public", website=True)
    def tournament_teams(self, tournament_slug=None, tournament_id=None, tournament=False, **kw):
        tournament = self._resolve_tournament(tournament_slug=tournament_slug, tournament_id=tournament_id, tournament=tournament)
        if not tournament.exists() or not tournament.can_access_public_detail():
            return request.not_found()
        if tournament_slug:
            redirect = self._canonical_redirect(tournament, tournament_slug, tournament.get_public_teams_path)
            if redirect:
                return redirect
        else:
            return request.redirect(tournament.get_public_teams_path())

        values = {
            "tournament": tournament,
            "participants": tournament.get_public_participants(),
            "page_name": "competition_teams",
        }
        return request.render("sports_federation_public_site.page_competition_teams", values)

    @http.route([
        "/tournaments/<string:tournament_slug>/standings",
        "/tournament/<int:tournament_id>/standings",
        "/competitions/<model('federation.tournament'):tournament>/standings",
    ], type="http", auth="public", website=True)
    def tournament_standings(self, tournament_slug=None, tournament_id=None, tournament=False, **kw):
        tournament = self._resolve_tournament(tournament_slug=tournament_slug, tournament_id=tournament_id, tournament=tournament)
        if not tournament.exists() or not tournament.can_access_public_standings():
            return request.not_found()
        if tournament_slug:
            redirect = self._canonical_redirect(tournament, tournament_slug, tournament.get_public_standings_path)
            if redirect:
                return redirect
        else:
            return request.redirect(tournament.get_public_standings_path())

        values = {
            "tournament": tournament,
            "standings": tournament.get_public_standings(),
            "page_name": "competition_standings",
        }
        return request.render("sports_federation_public_site.page_competition_standings", values)

    @http.route([
        "/tournaments/<string:tournament_slug>/results",
        "/tournament/<int:tournament_id>/results",
        "/competitions/<model('federation.tournament'):tournament>/results",
    ], type="http", auth="public", website=True)
    def tournament_results(self, tournament_slug=None, tournament_id=None, tournament=False, **kw):
        tournament = self._resolve_tournament(tournament_slug=tournament_slug, tournament_id=tournament_id, tournament=tournament)
        if not tournament.exists() or not tournament.can_access_public_results():
            return request.not_found()
        if tournament_slug:
            redirect = self._canonical_redirect(tournament, tournament_slug, tournament.get_public_results_path)
            if redirect:
                return redirect
        else:
            return request.redirect(tournament.get_public_results_path())

        values = {
            "tournament": tournament,
            "matches": tournament.get_public_result_matches(),
            "page_name": "competition_results",
        }
        return request.render("sports_federation_public_site.page_competition_results", values)

    @http.route([
        "/tournaments/<string:tournament_slug>/schedule",
        "/tournament/<int:tournament_id>/schedule",
        "/competitions/<model('federation.tournament'):tournament>/schedule",
    ], type="http", auth="public", website=True)
    def tournament_schedule(self, tournament_slug=None, tournament_id=None, tournament=False, **kw):
        tournament = self._resolve_tournament(tournament_slug=tournament_slug, tournament_id=tournament_id, tournament=tournament)
        if not tournament.exists() or not tournament.can_access_public_detail():
            return request.not_found()
        if tournament_slug:
            redirect = self._canonical_redirect(tournament, tournament_slug, tournament.get_public_schedule_path)
            if redirect:
                return redirect
        else:
            return request.redirect(tournament.get_public_schedule_path())

        values = {
            "tournament": tournament,
            "schedule_sections": tournament.get_public_schedule_sections(),
            "page_name": "competition_schedule",
        }
        return request.render("sports_federation_public_site.page_competition_schedule", values)

    @http.route([
        "/tournaments/<string:tournament_slug>/bracket",
        "/tournament/<int:tournament_id>/bracket",
        "/competitions/<model('federation.tournament'):tournament>/bracket",
    ], type="http", auth="public", website=True)
    def tournament_bracket(self, tournament_slug=None, tournament_id=None, tournament=False, **kw):
        tournament = self._resolve_tournament(tournament_slug=tournament_slug, tournament_id=tournament_id, tournament=tournament)
        if not tournament.exists() or not tournament.can_access_public_detail() or not tournament.has_public_bracket():
            return request.not_found()
        if tournament_slug:
            redirect = self._canonical_redirect(tournament, tournament_slug, tournament.get_public_bracket_path)
            if redirect:
                return redirect
        else:
            return request.redirect(tournament.get_public_bracket_path())

        values = {
            "tournament": tournament,
            "bracket_sections": tournament.get_public_bracket_sections(),
            "page_name": "competition_bracket",
        }
        return request.render("sports_federation_public_site.page_competition_bracket", values)

    @http.route([
        "/tournaments/<string:tournament_slug>/schedule.ics",
        "/tournament/<int:tournament_id>/schedule.ics",
    ], type="http", auth="public", methods=["GET"])
    def tournament_schedule_ics(self, tournament_slug=None, tournament_id=None, **kw):
        tournament = self._resolve_tournament(tournament_slug=tournament_slug, tournament_id=tournament_id)
        if not tournament.exists() or not tournament.can_access_public_detail():
            return request.not_found()
        if tournament_slug:
            redirect = self._canonical_redirect(tournament, tournament_slug, tournament.get_public_schedule_ics_path)
            if redirect:
                return redirect
        content = tournament.get_public_schedule_ics()
        filename = f"{tournament.get_public_slug_value()}-schedule.ics"
        return Response(
            content,
            content_type="text/calendar; charset=utf-8",
            headers=[
                ("Content-Disposition", f'attachment; filename="{filename}"'),
                ("X-Federation-Contract", "tournament_schedule_ics"),
                ("X-Federation-Contract-Version", "ics_v1"),
            ],
        )

    @http.route([
        "/api/v1/tournaments/<string:tournament_slug>/feed",
        "/api/v1/tournaments/<int:tournament_id>/feed",
        "/api/v1/competitions/<int:tournament_id>/feed",
    ], type="http", auth="public", methods=["GET"])
    def competition_feed_v1(self, tournament_slug=None, tournament_id=None, **kw):
        tournament = self._resolve_tournament(tournament_slug=tournament_slug, tournament_id=tournament_id)
        if not tournament.exists() or not tournament.can_access_public_detail():
            return request.not_found()
        return Response(
            json.dumps(tournament.get_public_feed_payload()),
            content_type="application/json; charset=utf-8",
            headers=[
                ("X-Federation-Contract", "tournament_feed"),
                ("X-Federation-Contract-Version", "v1"),
            ],
        )

    @http.route(["/teams/<string:team_slug>"], type="http", auth="public", website=True)
    def team_detail(self, team_slug, **kw):
        team = self._resolve_team(team_slug)
        if not team.exists() or not team.can_access_public_profile():
            return request.not_found()

        redirect = self._canonical_redirect(team, team_slug, team.get_public_path)
        if redirect:
            return redirect

        values = {
            "team": team,
            "public_tournaments": team.get_public_tournaments(limit=8),
            "upcoming_matches": team.get_public_upcoming_matches(limit=4),
            "recent_results": team.get_public_recent_result_matches(limit=4),
            "standing_lines": team.get_public_standing_lines(limit=8),
            "page_name": "public_team_profile",
        }
        return request.render("sports_federation_public_site.page_public_team_profile", values)