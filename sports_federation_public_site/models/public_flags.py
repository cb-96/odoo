from odoo import fields, models


class FederationTournament(models.Model):
    _inherit = "federation.tournament"

    _public_slug_unique = models.Constraint(
        "UNIQUE(public_slug)",
        "Public slug must be unique.",
    )

    website_published = fields.Boolean(
        string="Published on Website",
        default=False,
    )
    public_description = fields.Html(
        string="Public Description",
    )
    public_slug = fields.Char(
        string="Public Slug",
        help="Optional SEO/public URL slug override",
    )
    show_public_results = fields.Boolean(
        string="Show Public Results",
        default=True,
    )
    show_public_standings = fields.Boolean(
        string="Show Public Standings",
        default=True,
    )

    def can_access_public_detail(self):
        self.ensure_one()
        return bool(self.website_published)

    def get_public_result_matches(self):
        self.ensure_one()
        return self.env["federation.match"].sudo().search([
            ("tournament_id", "=", self.id),
            ("result_state", "=", "approved"),
        ], order="scheduled_date asc, date_scheduled asc, id asc")

    def get_public_schedule_matches(self):
        self.ensure_one()
        return self.env["federation.match"].sudo().search([
            ("tournament_id", "=", self.id),
            ("state", "in", ("draft", "scheduled", "in_progress")),
        ], order="scheduled_date asc, date_scheduled asc, round_number asc, id asc")

    def get_public_schedule_sections(self):
        self.ensure_one()
        Match = self.env["federation.match"].sudo().browse([])
        sections = []
        section_index = {}

        for match in self.get_public_schedule_matches():
            if match.round_id:
                key = f"round-{match.round_id.id}"
                title = match.round_id.name
                subtitle = fields.Date.to_string(match.round_id.round_date) if match.round_id.round_date else False
            elif match.stage_id:
                key = f"stage-{match.stage_id.id}"
                title = match.stage_id.name
                subtitle = fields.Date.to_string(match.scheduled_date) if match.scheduled_date else False
            elif match.scheduled_date:
                key = f"date-{match.scheduled_date}"
                title = fields.Date.to_string(match.scheduled_date)
                subtitle = False
            else:
                key = "unscheduled"
                title = "Unscheduled"
                subtitle = False

            if key not in section_index:
                section_index[key] = len(sections)
                sections.append(
                    {
                        "key": key,
                        "title": title,
                        "subtitle": subtitle,
                        "matches": Match,
                    }
                )
            sections[section_index[key]]["matches"] |= match

        return sections

    def has_public_bracket(self):
        self.ensure_one()
        return bool(self.get_public_bracket_sections())

    def get_public_bracket_sections(self):
        self.ensure_one()
        Match = self.env["federation.match"].sudo().browse([])
        bracket_matches = self.env["federation.match"].sudo().search(
            [
                ("tournament_id", "=", self.id),
                "|",
                ("bracket_type", "!=", False),
                "|",
                ("source_match_1_id", "!=", False),
                ("source_match_2_id", "!=", False),
            ],
            order="round_number asc, date_scheduled asc, id asc",
        )
        sections = []
        section_index = {}
        bracket_labels = dict(self.env["federation.match"]._fields["bracket_type"].selection)

        for match in bracket_matches:
            round_label = f"Round {match.round_number}" if match.round_number else "Bracket"
            bracket_label = bracket_labels.get(match.bracket_type, "Main")
            title = f"{bracket_label} {round_label}"
            key = f"{match.bracket_type or 'main'}-{match.round_number or 0}"

            if key not in section_index:
                section_index[key] = len(sections)
                sections.append(
                    {
                        "key": key,
                        "title": title,
                        "matches": Match,
                    }
                )
            sections[section_index[key]]["matches"] |= match

        return sections

    def _serialize_public_match(self, match):
        return {
            "id": match.id,
            "name": match.name,
            "state": match.state,
            "result_state": match.result_state if "result_state" in match._fields else False,
            "stage": match.stage_id.name if match.stage_id else None,
            "round": match.round_id.name if match.round_id else None,
            "round_number": match.round_number or None,
            "bracket_type": match.bracket_type or None,
            "scheduled_date": fields.Date.to_string(match.scheduled_date) if match.scheduled_date else None,
            "kickoff": fields.Datetime.to_string(match.date_scheduled) if match.date_scheduled else None,
            "home_team": match.home_team_id.name if match.home_team_id else None,
            "away_team": match.away_team_id.name if match.away_team_id else None,
            "home_score": match.home_score,
            "away_score": match.away_score,
            "venue": match.venue_id.name if "venue_id" in match._fields and match.venue_id else None,
            "playing_area": match.playing_area_id.name if "playing_area_id" in match._fields and match.playing_area_id else None,
            "source_match_1": match.source_match_1_id.name if match.source_match_1_id else None,
            "source_match_2": match.source_match_2_id.name if match.source_match_2_id else None,
        }

    def get_public_feed_payload(self):
        self.ensure_one()
        participants = self.env["federation.tournament.participant"].sudo().search([
            ("tournament_id", "=", self.id),
            ("state", "!=", "withdrawn"),
        ], order="state asc, team_id asc")
        standings = self.env["federation.standing"].sudo().search([
            ("tournament_id", "=", self.id),
            ("website_published", "=", True),
        ], order="stage_id asc, group_id asc, id asc")

        return {
            "api_version": "v1",
            "tournament": {
                "id": self.id,
                "name": self.name,
                "code": self.code,
                "state": self.state,
                "date_start": fields.Date.to_string(self.date_start) if self.date_start else None,
                "date_end": fields.Date.to_string(self.date_end) if self.date_end else None,
                "public_slug": self.public_slug or None,
                "show_public_results": self.show_public_results,
                "show_public_standings": self.show_public_standings,
            },
            "participants": [
                {
                    "id": participant.id,
                    "team": participant.team_id.name if participant.team_id else None,
                    "club": participant.club_id.name if participant.club_id else None,
                    "state": participant.state,
                }
                for participant in participants
            ],
            "schedule_sections": [
                {
                    "title": section["title"],
                    "subtitle": section["subtitle"],
                    "matches": [self._serialize_public_match(match) for match in section["matches"]],
                }
                for section in self.get_public_schedule_sections()
            ],
            "bracket_sections": [
                {
                    "title": section["title"],
                    "matches": [self._serialize_public_match(match) for match in section["matches"]],
                }
                for section in self.get_public_bracket_sections()
            ],
            "results": [self._serialize_public_match(match) for match in self.get_public_result_matches()],
            "standings": [
                {
                    "id": standing.id,
                    "name": standing.public_title or standing.name,
                    "stage": standing.stage_id.name if standing.stage_id else None,
                    "group": standing.group_id.name if standing.group_id else None,
                    "lines": [
                        {
                            "rank": line.rank,
                            "team": line.team_id.name if line.team_id else None,
                            "played": line.played,
                            "won": line.won,
                            "drawn": line.drawn,
                            "lost": line.lost,
                            "score_for": line.score_for,
                            "score_against": line.score_against,
                            "score_diff": line.score_diff,
                            "points": line.points,
                        }
                        for line in standing.line_ids.sorted(lambda record: record.rank)
                    ],
                }
                for standing in standings
            ],
        }

    def write(self, vals):
        to_publish = self.env["federation.tournament"].browse([])
        if vals.get("website_published"):
            to_publish = self.filtered(lambda record: not record.website_published)

        res = super().write(vals)

        if vals.get("website_published"):
            Dispatcher = self.env.get("federation.notification.dispatcher")
            if Dispatcher is not None:
                for record in to_publish.filtered("website_published"):
                    Dispatcher.send_tournament_published(record)

        return res

    def can_access_public_results(self):
        self.ensure_one()
        return bool(self.can_access_public_detail() and self.show_public_results)

    def can_access_public_standings(self):
        self.ensure_one()
        return bool(self.can_access_public_detail() and self.show_public_standings)


class FederationStanding(models.Model):
    _inherit = "federation.standing"

    website_published = fields.Boolean(
        string="Published on Website",
        default=False,
    )
    public_title = fields.Char(
        string="Public Title",
    )