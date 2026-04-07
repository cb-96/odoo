"""
KPI CSV export controller.

Endpoints
---------
GET /reporting/export/standings/<tournament_id>
    Download standings lines for a tournament as CSV.
    Columns: rank, team, club, played, won, drawn, lost, gf, ga, gd, points

GET /reporting/export/participation/<season_id>
    Download participation summary for a season as CSV.
    Columns: tournament, team, club, state

Access is restricted to authenticated internal users (auth="user").
"""
import csv
import io

from odoo import http
from odoo.http import request, Response


class KpiExportController(http.Controller):

    # ------------------------------------------------------------------
    # Standings CSV
    # ------------------------------------------------------------------

    @http.route(
        "/reporting/export/standings/<int:tournament_id>",
        type="http",
        auth="user",
        methods=["GET"],
    )
    def export_standings_csv(self, tournament_id, **kw):
        """Return a CSV file of all standing lines for a tournament."""
        tournament = request.env["federation.tournament"].browse(tournament_id)
        if not tournament.exists():
            return request.not_found()

        standings = request.env["federation.standing"].search([
            ("tournament_id", "=", tournament_id),
        ], order="name asc")

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Standing", "Rank", "Team", "Club",
            "Played", "Won", "Drawn", "Lost",
            "GF", "GA", "GD", "Points", "Tiebreak Notes",
        ])
        for standing in standings:
            for line in standing.line_ids.sorted(lambda l: l.rank):
                writer.writerow([
                    standing.name,
                    line.rank,
                    line.team_id.name if line.team_id else "",
                    line.club_id.name if line.club_id else "",
                    line.played,
                    line.won,
                    line.drawn,
                    line.lost,
                    line.score_for,
                    line.score_against,
                    line.score_diff,
                    line.points,
                    line.tiebreak_notes or "",
                ])

        filename = f"standings_{tournament.code or tournament_id}.csv"
        return Response(
            output.getvalue(),
            content_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    # ------------------------------------------------------------------
    # Participation CSV
    # ------------------------------------------------------------------

    @http.route(
        "/reporting/export/participation/<int:season_id>",
        type="http",
        auth="user",
        methods=["GET"],
    )
    def export_participation_csv(self, season_id, **kw):
        """Return a CSV file of participant registrations for a season."""
        season = request.env["federation.season"].browse(season_id)
        if not season.exists():
            return request.not_found()

        participants = request.env["federation.tournament.participant"].search([
            ("tournament_id.season_id", "=", season_id),
        ], order="tournament_id asc, team_id asc")

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Tournament", "Season", "Team", "Club", "State",
        ])
        for p in participants:
            writer.writerow([
                p.tournament_id.name if p.tournament_id else "",
                p.tournament_id.season_id.name if p.tournament_id.season_id else "",
                p.team_id.name if p.team_id else "",
                p.club_id.name if p.club_id else "",
                p.state or "",
            ])

        filename = f"participation_{season.code or season_id}.csv"
        return Response(
            output.getvalue(),
            content_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
