import re
import unicodedata
from datetime import timedelta

from odoo import api, fields, models


_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def _slugify_public_text(value):
    """Handle slugify public text."""
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = _SLUG_PATTERN.sub("-", ascii_value).strip("-")
    return slug or "item"


def _ics_escape(value):
    """Handle ICS escape."""
    if not value:
        return ""
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _ics_format_datetime(value):
    """Handle ICS format datetime."""
    return fields.Datetime.to_datetime(value).strftime("%Y%m%dT%H%M%S")


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
    public_featured = fields.Boolean(
        string="Featured on Tournament Hub",
        default=False,
    )
    public_editorial_summary = fields.Text(
        string="Editorial Summary",
        help="Short front-page summary shown on public tournament cards and hero sections.",
    )
    public_pinned_announcement = fields.Text(
        string="Pinned Announcement",
        help="Short notice displayed prominently on the public tournament page.",
    )
    public_hero_image = fields.Binary(
        string="Public Hero Image",
    )

    def _normalize_public_slug_vals(self, vals):
        """Normalize public slug vals."""
        normalized = dict(vals)
        if "public_slug" in normalized:
            normalized["public_slug"] = _slugify_public_text(normalized["public_slug"]) if normalized.get("public_slug") else False
        return normalized

    def _get_public_slug_seed(self):
        """Return public slug seed."""
        self.ensure_one()
        return self.public_slug or self.name or self.code or "tournament"

    def get_public_slug_value(self):
        """Return public slug value."""
        self.ensure_one()
        if self.public_slug:
            return self.public_slug
        return f"{_slugify_public_text(self._get_public_slug_seed())}-{self.id}"

    @api.model
    def resolve_public_slug(self, slug_value):
        """Resolve public slug."""
        if not slug_value:
            return self.browse([])

        explicit = self.sudo().search([("public_slug", "=", slug_value)], limit=1)
        if explicit:
            return explicit

        tail = slug_value.rsplit("-", 1)[-1]
        if not tail.isdigit():
            return self.browse([])

        record = self.sudo().browse(int(tail))
        if record.exists() and record.get_public_slug_value() == slug_value:
            return record
        return self.browse([])

    def get_public_path(self):
        """Return public path."""
        self.ensure_one()
        return f"/tournaments/{self.get_public_slug_value()}"

    def get_public_register_path(self):
        """Return public register path."""
        self.ensure_one()
        return f"{self.get_public_path()}/register"

    def get_public_teams_path(self):
        """Return public teams path."""
        self.ensure_one()
        return f"{self.get_public_path()}/teams"

    def get_public_schedule_path(self):
        """Return public schedule path."""
        self.ensure_one()
        return f"{self.get_public_path()}/schedule"

    def get_public_results_path(self):
        """Return public results path."""
        self.ensure_one()
        return f"{self.get_public_path()}/results"

    def get_public_standings_path(self):
        """Return public standings path."""
        self.ensure_one()
        return f"{self.get_public_path()}/standings"

    def get_public_bracket_path(self):
        """Return public bracket path."""
        self.ensure_one()
        return f"{self.get_public_path()}/bracket"

    def get_public_feed_path(self):
        """Return public feed path."""
        self.ensure_one()
        return f"/api/v1/tournaments/{self.get_public_slug_value()}/feed"

    def get_public_schedule_ics_path(self):
        """Return public schedule ICS path."""
        self.ensure_one()
        return f"{self.get_public_path()}/schedule.ics"

    @api.model
    def _get_public_site_search_domain(self, search=None):
        """Return public site search domain."""
        if not search:
            return []

        search_terms = [("name", "ilike", search)]
        if "code" in self._fields:
            search_terms.append(("code", "ilike", search))
        if "location" in self._fields:
            search_terms.append(("location", "ilike", search))
        if "venue_id" in self._fields:
            search_terms.append(("venue_id.name", "ilike", search))
        if "public_editorial_summary" in self._fields:
            search_terms.append(("public_editorial_summary", "ilike", search))

        if len(search_terms) == 1:
            return [search_terms[0]]
        return ["|"] * (len(search_terms) - 1) + search_terms

    @api.model
    def get_public_published_tournaments(self, search=None, limit=None, extra_domain=None):
        """Return public published tournaments."""
        tournaments = self.sudo().search(
            [("website_published", "=", True)] + self._get_public_site_search_domain(search) + list(extra_domain or []),
            order="date_start asc, id asc",
        )
        return tournaments[:limit] if limit else tournaments

    @api.model
    def get_public_featured_tournaments(self, search=None, limit=None, extra_domain=None):
        """Return public featured tournaments."""
        domain = [
            ("website_published", "=", True),
            ("state", "in", ("open", "in_progress")),
        ] + self._get_public_site_search_domain(search) + list(extra_domain or [])
        tournaments = self.sudo().search(domain, order="date_start asc, id asc")
        featured = tournaments.filtered("public_featured")
        ordered = featured + (tournaments - featured)
        return ordered[:limit] if limit else ordered

    @api.model
    def get_public_archived_tournaments(self, search=None, limit=None, extra_domain=None):
        """Return public archived tournaments."""
        domain = [
            ("website_published", "=", True),
            ("state", "in", ("closed", "cancelled")),
        ] + self._get_public_site_search_domain(search) + list(extra_domain or [])
        tournaments = self.sudo().search(domain, order="date_start desc, id desc")
        return tournaments[:limit] if limit else tournaments

    @api.model
    def get_public_live_tournaments(self, limit=None, extra_domain=None):
        """Return public live tournaments."""
        domain = [
            ("website_published", "=", True),
            ("state", "=", "in_progress"),
        ] + list(extra_domain or [])
        tournaments = self.sudo().search(domain, order="date_start desc, id desc")
        featured = tournaments.filtered("public_featured")
        ordered = featured + (tournaments - featured)
        return ordered[:limit] if limit else ordered

    @api.model
    def get_public_recent_result_tournaments(self, limit=None, extra_domain=None):
        """Return public recent result tournaments."""
        tournaments = self.sudo().search(
            [
                ("website_published", "=", True),
                ("state", "in", ("open", "in_progress", "closed")),
            ] + list(extra_domain or []),
            order="write_date desc, id desc",
        )
        ranked = []
        Match = self.env["federation.match"].sudo()
        for tournament in tournaments:
            latest_match = Match.search(
                [
                    ("tournament_id", "=", tournament.id),
                    ("result_state", "=", "approved"),
                ],
                order="date_scheduled desc, write_date desc, id desc",
                limit=1,
            )
            if not latest_match:
                continue
            activity_dt = latest_match.date_scheduled or latest_match.write_date or tournament.write_date
            ranked.append((activity_dt, tournament.id))
        ranked.sort(reverse=True)
        result_ids = [tournament_id for _, tournament_id in ranked[:limit]] if limit else [tournament_id for _, tournament_id in ranked]
        return self.browse(result_ids)

    def can_access_public_detail(self):
        """Return whether access public detail is allowed."""
        self.ensure_one()
        return bool(self.website_published)

    def get_public_standings(self):
        """Return public standings."""
        self.ensure_one()
        return self.env["federation.standing"].sudo().search([
            ("tournament_id", "=", self.id),
            ("website_published", "=", True),
        ], order="stage_id asc, group_id asc, id asc")

    def get_public_participants(self, limit=None):
        """Return public participants."""
        self.ensure_one()
        participants = self.env["federation.tournament.participant"].sudo().search([
            ("tournament_id", "=", self.id),
            ("state", "!=", "withdrawn"),
        ], order="state asc, team_id asc, id asc")
        return participants[:limit] if limit else participants

    def get_public_result_matches(self):
        """Return public result matches."""
        self.ensure_one()
        return self.env["federation.match"].sudo().search([
            ("tournament_id", "=", self.id),
            ("result_state", "=", "approved"),
        ], order="scheduled_date asc, date_scheduled asc, id asc")

    def get_public_recent_result_matches(self, limit=None):
        """Return public recent result matches."""
        self.ensure_one()
        matches = self.env["federation.match"].sudo().search([
            ("tournament_id", "=", self.id),
            ("result_state", "=", "approved"),
        ], order="date_scheduled desc, scheduled_date desc, id desc")
        return matches[:limit] if limit else matches

    def get_public_schedule_matches(self):
        """Return public schedule matches."""
        self.ensure_one()
        return self.env["federation.match"].sudo().search([
            ("tournament_id", "=", self.id),
            ("state", "in", ("draft", "scheduled", "in_progress")),
        ], order="scheduled_date asc, date_scheduled asc, round_number asc, id asc")

    def get_public_live_matches(self, limit=None):
        """Return public live matches."""
        self.ensure_one()
        matches = self.env["federation.match"].sudo().search([
            ("tournament_id", "=", self.id),
            ("state", "=", "in_progress"),
        ], order="date_scheduled asc, id asc")
        return matches[:limit] if limit else matches

    def get_public_upcoming_matches(self, limit=None):
        """Return public upcoming matches."""
        self.ensure_one()
        matches = self.env["federation.match"].sudo().search([
            ("tournament_id", "=", self.id),
            ("state", "in", ("draft", "scheduled", "in_progress")),
        ], order="date_scheduled asc, scheduled_date asc, id asc")
        matches = matches.filtered(lambda record: record.date_scheduled or record.scheduled_date)
        return matches[:limit] if limit else matches

    def get_public_schedule_sections(self):
        """Return public schedule sections."""
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
        """Return whether the record has public bracket."""
        self.ensure_one()
        return bool(self.get_public_bracket_sections())

    def get_public_bracket_sections(self):
        """Return public bracket sections."""
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
        """Serialize public match."""
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
            "home_team_url": match.home_team_id.get_public_path() if match.home_team_id else None,
            "away_team": match.away_team_id.name if match.away_team_id else None,
            "away_team_url": match.away_team_id.get_public_path() if match.away_team_id else None,
            "home_score": match.home_score,
            "away_score": match.away_score,
            "venue": match.venue_id.name if "venue_id" in match._fields and match.venue_id else None,
            "playing_area": match.playing_area_id.name if "playing_area_id" in match._fields and match.playing_area_id else None,
            "source_match_1": match.source_match_1_id.name if match.source_match_1_id else None,
            "source_match_2": match.source_match_2_id.name if match.source_match_2_id else None,
        }

    def get_public_schedule_ics(self):
        """Return public schedule ICS."""
        self.ensure_one()
        events = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Sports Federation//Tournament Schedule//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            f"X-WR-CALNAME:{_ics_escape(self.name)}",
        ]
        for match in self.get_public_schedule_matches().filtered("date_scheduled"):
            start_dt = fields.Datetime.to_datetime(match.date_scheduled)
            end_dt = start_dt + timedelta(hours=1)
            summary = f"{match.home_team_id.name if match.home_team_id else 'TBD'} vs {match.away_team_id.name if match.away_team_id else 'TBD'}"
            location_parts = []
            if "venue_id" in match._fields and match.venue_id:
                location_parts.append(match.venue_id.name)
            if "playing_area_id" in match._fields and match.playing_area_id:
                location_parts.append(match.playing_area_id.name)

            description_parts = [self.name]
            if match.round_id:
                description_parts.append(match.round_id.name)
            if match.stage_id:
                description_parts.append(match.stage_id.name)

            events.extend([
                "BEGIN:VEVENT",
                f"UID:tournament-{self.id}-match-{match.id}@sportsfederation",
                f"DTSTAMP:{_ics_format_datetime(fields.Datetime.now())}",
                f"DTSTART:{_ics_format_datetime(start_dt)}",
                f"DTEND:{_ics_format_datetime(end_dt)}",
                f"SUMMARY:{_ics_escape(summary)}",
                f"DESCRIPTION:{_ics_escape(' | '.join(description_parts))}",
                f"LOCATION:{_ics_escape(', '.join(location_parts))}",
                f"URL:{_ics_escape(self.get_public_schedule_path())}",
                "END:VEVENT",
            ])
        events.append("END:VCALENDAR")
        return "\r\n".join(events) + "\r\n"

    def get_public_feed_payload(self):
        """Return public feed payload."""
        self.ensure_one()
        participants = self.get_public_participants()
        standings = self.get_public_standings()

        return {
            "api_version": "v1",
            "tournament": {
                "id": self.id,
                "name": self.name,
                "slug": self.get_public_slug_value(),
                "code": self.code,
                "state": self.state,
                "date_start": fields.Date.to_string(self.date_start) if self.date_start else None,
                "date_end": fields.Date.to_string(self.date_end) if self.date_end else None,
                "public_slug": self.public_slug or None,
                "public_url": self.get_public_path(),
                "register_url": self.get_public_register_path(),
                "teams_url": self.get_public_teams_path(),
                "schedule_url": self.get_public_schedule_path(),
                "results_url": self.get_public_results_path(),
                "standings_url": self.get_public_standings_path(),
                "bracket_url": self.get_public_bracket_path(),
                "feed_url": self.get_public_feed_path(),
                "schedule_ics_url": self.get_public_schedule_ics_path(),
                "show_public_results": self.show_public_results,
                "show_public_standings": self.show_public_standings,
                "featured": self.public_featured,
                "editorial_summary": self.public_editorial_summary or None,
                "pinned_announcement": self.public_pinned_announcement or None,
            },
            "participants": [
                {
                    "id": participant.id,
                    "team": participant.team_id.name if participant.team_id else None,
                    "team_url": participant.team_id.get_public_path() if participant.team_id else None,
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
                            "team_url": line.team_id.get_public_path() if line.team_id else None,
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

    @api.model_create_multi
    def create(self, vals_list):
        """Create records with module-specific defaults and side effects."""
        return super().create([self._normalize_public_slug_vals(vals) for vals in vals_list])

    def write(self, vals):
        """Update records with module-specific side effects."""
        vals = self._normalize_public_slug_vals(vals)
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
        """Return whether access public results is allowed."""
        self.ensure_one()
        return bool(self.can_access_public_detail() and self.show_public_results)

    def can_access_public_standings(self):
        """Return whether access public standings is allowed."""
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


class FederationTeam(models.Model):
    _inherit = "federation.team"

    _public_slug_unique = models.Constraint(
        "UNIQUE(public_slug)",
        "Public team slug must be unique.",
    )

    public_slug = fields.Char(
        string="Public Slug",
        help="Optional readable slug seed for public team pages.",
    )

    def _normalize_public_slug_vals(self, vals):
        """Normalize public slug vals."""
        normalized = dict(vals)
        if "public_slug" in normalized:
            normalized["public_slug"] = _slugify_public_text(normalized["public_slug"]) if normalized.get("public_slug") else False
        return normalized

    def _get_public_slug_seed(self):
        """Return public slug seed."""
        self.ensure_one()
        if self.public_slug:
            return self.public_slug
        club_name = self.club_id.name if self.club_id else False
        return "-".join(filter(None, [self.name, club_name])) or self.code or "team"

    def get_public_slug_value(self):
        """Return public slug value."""
        self.ensure_one()
        if self.public_slug:
            return self.public_slug
        return f"{_slugify_public_text(self._get_public_slug_seed())}-{self.id}"

    @api.model
    def resolve_public_slug(self, slug_value):
        """Resolve public slug."""
        if not slug_value:
            return self.browse([])

        explicit = self.sudo().search([("public_slug", "=", slug_value)], limit=1)
        if explicit:
            return explicit

        tail = slug_value.rsplit("-", 1)[-1]
        if not tail.isdigit():
            return self.browse([])

        record = self.sudo().browse(int(tail))
        if record.exists() and record.get_public_slug_value() == slug_value:
            return record
        return self.browse([])

    def get_public_path(self):
        """Return public path."""
        self.ensure_one()
        return f"/teams/{self.get_public_slug_value()}"

    def can_access_public_profile(self):
        """Return whether access public profile is allowed."""
        self.ensure_one()
        Participant = self.env["federation.tournament.participant"].sudo()
        if Participant.search_count(
            [
                ("team_id", "=", self.id),
                ("state", "!=", "withdrawn"),
                ("tournament_id.website_published", "=", True),
            ],
            limit=1,
        ):
            return True

        Match = self.env["federation.match"].sudo()
        return bool(
            Match.search_count(
                [
                    ("tournament_id.website_published", "=", True),
                    "|",
                    ("home_team_id", "=", self.id),
                    ("away_team_id", "=", self.id),
                ],
                limit=1,
            )
        )

    def get_public_tournaments(self, limit=None):
        """Return public tournaments."""
        self.ensure_one()
        tournaments = self.env["federation.tournament"].sudo().search(
            [
                ("website_published", "=", True),
                ("participant_ids.team_id", "=", self.id),
            ],
            order="date_start desc, id desc",
        )
        return tournaments[:limit] if limit else tournaments

    def get_public_recent_result_matches(self, limit=None):
        """Return public recent result matches."""
        self.ensure_one()
        matches = self.env["federation.match"].sudo().search(
            [
                ("tournament_id.website_published", "=", True),
                ("result_state", "=", "approved"),
                "|",
                ("home_team_id", "=", self.id),
                ("away_team_id", "=", self.id),
            ],
            order="date_scheduled desc, scheduled_date desc, id desc",
        )
        return matches[:limit] if limit else matches

    def get_public_upcoming_matches(self, limit=None):
        """Return public upcoming matches."""
        self.ensure_one()
        matches = self.env["federation.match"].sudo().search(
            [
                ("tournament_id.website_published", "=", True),
                ("state", "in", ("draft", "scheduled", "in_progress")),
                "|",
                ("home_team_id", "=", self.id),
                ("away_team_id", "=", self.id),
            ],
            order="date_scheduled asc, scheduled_date asc, id asc",
        )
        matches = matches.filtered(lambda record: record.date_scheduled or record.scheduled_date)
        return matches[:limit] if limit else matches

    def get_public_standing_lines(self, limit=None):
        """Return public standing lines."""
        self.ensure_one()
        lines = self.env["federation.standing.line"].sudo().search(
            [
                ("team_id", "=", self.id),
                ("standing_id.website_published", "=", True),
            ],
            order="id desc",
        )
        return lines[:limit] if limit else lines

    @api.model_create_multi
    def create(self, vals_list):
        """Create records with module-specific defaults and side effects."""
        return super().create([self._normalize_public_slug_vals(vals) for vals in vals_list])

    def write(self, vals):
        """Update records with module-specific side effects."""
        return super().write(self._normalize_public_slug_vals(vals))