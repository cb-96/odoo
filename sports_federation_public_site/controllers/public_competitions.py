from odoo import http
from odoo.http import request
from odoo.addons.website.controllers.main import Website


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