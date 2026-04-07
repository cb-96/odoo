from odoo import http
from odoo.http import request
from odoo.addons.website.controllers.main import Website
import json


class PublicCompetitionsController(http.Controller):

    @http.route("/competitions", type="http", auth="public", website=True)
    def competitions_list(self, **kw):
        """Public list page of all published tournaments."""
        tournaments = request.env["federation.tournament"].sudo().search([
            ("website_published", "=", True),
        ], order="date_start asc")
        values = {
            "tournaments": tournaments,
            "page_name": "competitions",
        }
        return request.render("sports_federation_public_site.page_competitions", values)

    @http.route("/competitions/archive", type="http", auth="public", website=True)
    def competitions_archive(self, **kw):
        """Public archive page — past (closed/cancelled) published tournaments."""
        tournaments = request.env["federation.tournament"].sudo().search([
            ("website_published", "=", True),
            ("state", "in", ("closed", "cancelled")),
        ], order="date_start desc")
        values = {
            "tournaments": tournaments,
            "page_name": "competitions_archive",
        }
        return request.render("sports_federation_public_site.page_competitions_archive", values)

    @http.route("/competitions/api/json", type="json", auth="public", methods=["POST"])
    def competitions_api_json(self, **kw):
        """JSON API endpoint — returns published tournament list.

        Response::

            {
                "tournaments": [
                    {"id": int, "name": str, "state": str,
                     "date_start": str|null, "date_end": str|null}
                ]
            }
        """
        tournaments = request.env["federation.tournament"].sudo().search([
            ("website_published", "=", True),
        ], order="date_start asc")
        result = []
        for t in tournaments:
            result.append({
                "id": t.id,
                "name": t.name,
                "state": t.state,
                "date_start": t.date_start.isoformat() if t.date_start else None,
                "date_end": t.date_end.isoformat() if t.date_end else None,
            })
        return {"tournaments": result}

    @http.route("/competitions/<model('federation.tournament'):tournament>", type="http", auth="public", website=True)
    def competition_detail(self, tournament, **kw):
        """Public tournament detail page."""
        if not tournament.website_published:
            return request.not_found()
        values = {
            "tournament": tournament,
            "page_name": "competition_detail",
        }
        return request.render("sports_federation_public_site.page_competition_detail", values)

    @http.route("/competitions/<model('federation.tournament'):tournament>/teams", type="http", auth="public", website=True)
    def competition_teams(self, tournament, **kw):
        """Public team listing for a tournament, ordered by participant state."""
        if not tournament.website_published:
            return request.not_found()
        participants = request.env["federation.tournament.participant"].sudo().search([
            ("tournament_id", "=", tournament.id),
            ("state", "!=", "withdrawn"),
        ], order="state asc, team_id asc")
        values = {
            "tournament": tournament,
            "participants": participants,
            "page_name": "competition_teams",
        }
        return request.render("sports_federation_public_site.page_competition_teams", values)

    @http.route("/competitions/<model('federation.tournament'):tournament>/standings", type="http", auth="public", website=True)
    def competition_standings(self, tournament, **kw):
        """Public standings page for one tournament."""
        if not tournament.website_published:
            return request.not_found()
        standings = request.env["federation.standing"].sudo().search([
            ("tournament_id", "=", tournament.id),
            ("website_published", "=", True),
        ])
        values = {
            "tournament": tournament,
            "standings": standings,
            "page_name": "competition_standings",
        }
        return request.render("sports_federation_public_site.page_competition_standings", values)

    @http.route("/competitions/<model('federation.tournament'):tournament>/results", type="http", auth="public", website=True)
    def competition_results(self, tournament, **kw):
        """Public results page for one tournament."""
        if not tournament.website_published:
            return request.not_found()
        matches = request.env["federation.match"].sudo().search([
            ("tournament_id", "=", tournament.id),
            ("result_state", "=", "approved"),
        ], order="date_scheduled asc")
        values = {
            "tournament": tournament,
            "matches": matches,
            "page_name": "competition_results",
        }
        return request.render("sports_federation_public_site.page_competition_results", values)

    @http.route("/competitions/<model('federation.tournament'):tournament>/schedule", type="http", auth="public", website=True)
    def competition_schedule(self, tournament, **kw):
        """Public schedule page for one tournament (alias for results)."""
        return self.competition_results(tournament, **kw)