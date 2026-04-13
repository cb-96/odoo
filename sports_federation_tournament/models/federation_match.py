from datetime import datetime, time

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class FederationMatch(models.Model):
    _name = "federation.match"
    _description = "Federation Match"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_scheduled desc, id"

    name = fields.Char(string="Reference", compute="_compute_name", store=True)
    tournament_id = fields.Many2one(
        "federation.tournament", string="Tournament", required=True, ondelete="cascade"
    )
    stage_id = fields.Many2one(
        "federation.tournament.stage", string="Stage", ondelete="set null"
    )
    group_id = fields.Many2one(
        "federation.tournament.group", string="Group", ondelete="set null"
    )
    home_team_id = fields.Many2one(
        "federation.team", string="Home Team", ondelete="restrict"
    )
    away_team_id = fields.Many2one(
        "federation.team", string="Away Team", ondelete="restrict"
    )
    date_scheduled = fields.Datetime(string="Kickoff", tracking=True)
    scheduled_date = fields.Date(
        string="Scheduled Date",
        compute="_compute_schedule_fields",
        store=True,
    )
    scheduled_time = fields.Float(
        string="Kickoff Time",
        compute="_compute_schedule_fields",
        inverse="_inverse_scheduled_time",
        store=True,
        help="Time of day for the match. The calendar date comes from the assigned round.",
    )
    round_id = fields.Many2one(
        "federation.tournament.round",
        string="Round",
        ondelete="set null",
    )
    round_number = fields.Integer(string="Round Number")
    bracket_position = fields.Integer(string="Bracket Position")
    bracket_type = fields.Selection(
        [
            ("winners", "Winners"),
            ("losers", "Losers"),
            ("consolation", "Consolation"),
            ("placement_3rd", "3rd Place"),
            ("placement_5th", "5th Place"),
            ("placement_7th", "7th Place"),
        ],
        string="Bracket Type",
    )
    source_match_1_id = fields.Many2one(
        "federation.match",
        string="Source Match 1",
        ondelete="set null",
        help="Winner or loser of this match feeds into the current match.",
    )
    source_match_2_id = fields.Many2one(
        "federation.match",
        string="Source Match 2",
        ondelete="set null",
    )
    source_type_1 = fields.Selection(
        [("winner", "Winner"), ("loser", "Loser")],
        string="Source 1 Type",
        default="winner",
    )
    source_type_2 = fields.Selection(
        [("winner", "Winner"), ("loser", "Loser")],
        string="Source 2 Type",
        default="winner",
    )
    next_match_ids = fields.One2many(
        "federation.match",
        compute="_compute_next_matches",
        string="Next Matches",
    )
    home_score = fields.Integer(string="Home Score", tracking=True)
    away_score = fields.Integer(string="Away Score", tracking=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("scheduled", "Scheduled"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )
    notes = fields.Text(string="Notes")

    @staticmethod
    def _float_to_time(float_value):
        total_seconds = int(round(float(float_value or 0.0) * 3600))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        hours = hours % 24
        return time(hour=hours, minute=minutes, second=seconds)

    @staticmethod
    def _time_to_float(datetime_value):
        return round(
            datetime_value.hour
            + (datetime_value.minute / 60.0)
            + (datetime_value.second / 3600.0),
            4,
        )

    @staticmethod
    def _has_scheduled_time(value):
        return value is not False and value is not None and value != ""

    def _get_schedule_context(self, vals=None, record=False):
        vals = vals or {}
        Round = self.env["federation.tournament.round"]

        if "round_id" in vals:
            round_record = Round.browse(vals["round_id"]) if vals["round_id"] else Round.browse([])
        else:
            round_record = record.round_id if record else Round.browse([])

        if "date_scheduled" in vals:
            schedule_dt = (
                fields.Datetime.to_datetime(vals["date_scheduled"])
                if vals["date_scheduled"]
                else False
            )
        elif record and record.date_scheduled:
            schedule_dt = fields.Datetime.to_datetime(record.date_scheduled)
        else:
            schedule_dt = False

        if "scheduled_time" in vals:
            schedule_time = vals["scheduled_time"]
        elif schedule_dt:
            schedule_time = self._time_to_float(schedule_dt)
        elif record:
            schedule_time = record.scheduled_time
        else:
            schedule_time = False

        schedule_date = round_record.round_date if round_record and round_record.round_date else False
        if not schedule_date and schedule_dt:
            schedule_date = schedule_dt.date()

        return round_record, schedule_date, schedule_time, schedule_dt

    def _normalize_schedule_vals(self, vals, record=False):
        prepared_vals = dict(vals)
        round_record, schedule_date, schedule_time, schedule_dt = self._get_schedule_context(
            prepared_vals,
            record=record,
        )

        if "scheduled_time" in prepared_vals and not self._has_scheduled_time(
            prepared_vals["scheduled_time"]
        ):
            prepared_vals["date_scheduled"] = False
            prepared_vals["scheduled_time"] = False
            return prepared_vals

        if "date_scheduled" in prepared_vals and not prepared_vals["date_scheduled"]:
            prepared_vals["date_scheduled"] = False
            prepared_vals["scheduled_time"] = False
            return prepared_vals

        if self._has_scheduled_time(schedule_time) and schedule_date:
            prepared_vals["date_scheduled"] = datetime.combine(
                schedule_date,
                self._float_to_time(schedule_time),
            )
            prepared_vals["scheduled_time"] = schedule_time
            return prepared_vals

        if schedule_dt:
            if round_record and round_record.round_date:
                schedule_dt = datetime.combine(round_record.round_date, schedule_dt.time())
                prepared_vals["date_scheduled"] = schedule_dt
            prepared_vals["scheduled_time"] = self._time_to_float(schedule_dt)
            return prepared_vals

        if record and "round_id" in prepared_vals and record.date_scheduled and round_record and round_record.round_date:
            current_dt = fields.Datetime.to_datetime(record.date_scheduled)
            prepared_vals["date_scheduled"] = datetime.combine(round_record.round_date, current_dt.time())
            prepared_vals["scheduled_time"] = self._time_to_float(current_dt)

        return prepared_vals

    def _apply_round_defaults(self, vals):
        round_id = vals.get("round_id")
        if not round_id:
            return vals

        round_record = self.env["federation.tournament.round"].browse(round_id)
        if not round_record.exists():
            return vals

        if round_record.tournament_id and not vals.get("tournament_id"):
            vals["tournament_id"] = round_record.tournament_id.id
        if round_record.stage_id and not vals.get("stage_id"):
            vals["stage_id"] = round_record.stage_id.id
        if round_record.group_id and not vals.get("group_id"):
            vals["group_id"] = round_record.group_id.id
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        prepared_vals_list = [
            self._normalize_schedule_vals(self._apply_round_defaults(dict(vals)))
            for vals in vals_list
        ]
        return super().create(prepared_vals_list)

    def write(self, vals):
        prepared_vals = dict(vals)
        if {"round_id", "date_scheduled", "scheduled_time"}.intersection(prepared_vals):
            result = True
            for record in self:
                record_vals = record._normalize_schedule_vals(
                    record._apply_round_defaults(dict(prepared_vals)),
                    record=record,
                )
                result = super(FederationMatch, record).write(record_vals) and result
            return result

        return super().write(prepared_vals)

    @api.depends("date_scheduled", "round_id.round_date")
    def _compute_schedule_fields(self):
        for rec in self:
            if rec.round_id and rec.round_id.round_date:
                rec.scheduled_date = rec.round_id.round_date
            elif rec.date_scheduled:
                rec.scheduled_date = fields.Datetime.to_datetime(rec.date_scheduled).date()
            else:
                rec.scheduled_date = False

            if rec.date_scheduled:
                rec.scheduled_time = self._time_to_float(
                    fields.Datetime.to_datetime(rec.date_scheduled)
                )
            else:
                rec.scheduled_time = False

    def _inverse_scheduled_time(self):
        if self.env.context.get("skip_scheduled_time_inverse"):
            return

        for rec in self:
            if not self._has_scheduled_time(rec.scheduled_time):
                rec.with_context(skip_scheduled_time_inverse=True).date_scheduled = False
                continue

            schedule_date = (
                rec.round_id.round_date if rec.round_id and rec.round_id.round_date else False
            )
            if not schedule_date and rec.date_scheduled:
                schedule_date = fields.Datetime.to_datetime(rec.date_scheduled).date()
            if not schedule_date:
                schedule_date = rec.scheduled_date
            if not schedule_date:
                continue

            rec.with_context(skip_scheduled_time_inverse=True).date_scheduled = (
                datetime.combine(
                    schedule_date,
                    self._float_to_time(rec.scheduled_time),
                )
            )

    @api.depends("home_team_id", "away_team_id")
    def _compute_name(self):
        for rec in self:
            if rec.home_team_id and rec.away_team_id:
                rec.name = f"{rec.home_team_id.name} vs {rec.away_team_id.name}"
            else:
                rec.name = "Match"

    @api.constrains("home_team_id", "away_team_id")
    def _check_teams(self):
        for rec in self:
            if rec.home_team_id and rec.away_team_id and rec.home_team_id == rec.away_team_id:
                raise ValidationError("Home and away teams cannot be the same.")

    @api.onchange("round_id")
    def _onchange_round_id(self):
        if not self.round_id:
            return
        if self.round_id.tournament_id and not self.tournament_id:
            self.tournament_id = self.round_id.tournament_id
        if self.round_id.stage_id and not self.stage_id:
            self.stage_id = self.round_id.stage_id
        if self.round_id.group_id and not self.group_id:
            self.group_id = self.round_id.group_id
        if self.round_id.round_date and self.date_scheduled:
            kickoff_dt = fields.Datetime.to_datetime(self.date_scheduled)
            self.date_scheduled = datetime.combine(self.round_id.round_date, kickoff_dt.time())

    @api.constrains("round_id", "tournament_id", "stage_id", "group_id", "date_scheduled")
    def _check_round_scope(self):
        for rec in self:
            if not rec.round_id:
                continue
            if rec.round_id.tournament_id and rec.round_id.tournament_id != rec.tournament_id:
                raise ValidationError(
                    _("A match can only use a round from the same tournament.")
                )
            if rec.round_id.stage_id and rec.round_id.stage_id != rec.stage_id:
                raise ValidationError(
                    _("A match can only use a round assigned to the same stage.")
                )
            if rec.round_id.group_id and rec.round_id.group_id != rec.group_id:
                raise ValidationError(
                    _("A match can only use a round assigned to the same group.")
                )
            if rec.round_id.round_date and rec.date_scheduled:
                scheduled_dt = fields.Datetime.to_datetime(rec.date_scheduled)
                if scheduled_dt.date() != rec.round_id.round_date:
                    raise ValidationError(
                        _("A scheduled match must use the same calendar date as its round.")
                    )

    def _compute_next_matches(self):
        for rec in self:
            rec.next_match_ids = self.search([
                "|",
                ("source_match_1_id", "=", rec.id),
                ("source_match_2_id", "=", rec.id),
            ])

    def _get_result_team(self, result_type):
        """Return the winner or loser team of a completed match."""
        self.ensure_one()
        if self.state != "done":
            return False
        if self.home_score > self.away_score:
            winner, loser = self.home_team_id, self.away_team_id
        elif self.away_score > self.home_score:
            winner, loser = self.away_team_id, self.home_team_id
        else:
            return False  # draw — cannot determine
        return winner if result_type == "winner" else loser

    def action_schedule(self):
        for rec in self:
            rec.state = "scheduled"

    def action_start(self):
        for rec in self:
            rec.state = "in_progress"

    def action_done(self):
        for rec in self:
            rec.state = "done"
            rec._advance_bracket_teams()

    def action_cancel(self):
        for rec in self:
            rec.state = "cancelled"

    def action_draft(self):
        for rec in self:
            rec.state = "draft"

    def action_create_venue_finance_event(self, fee_type_code="venue_booking", amount=None, partner=None, note=None):
        """Create a federation.finance.event for venue passthrough costs.

        This helper looks for a fee type with code `fee_type_code`, creates one
        if missing, and calls `federation.finance.event`.create_from_source.
        Returns the created finance event(s).
        """
        events = self.env["federation.finance.event"]
        FeeType = self.env["federation.fee.type"]

        for match in self:
            venue_name = ""
            if hasattr(match, 'venue_id') and match.venue_id:
                venue_name = match.venue_id.name
            if not venue_name:
                raise ValidationError("Match has no venue set; cannot create finance event.")

            fee_type = FeeType.search([("code", "=", fee_type_code)], limit=1)
            if not fee_type:
                # create a sensible default fee type for venue charges
                fee_type = FeeType.create({
                    "name": "Venue Booking",
                    "code": fee_type_code,
                    "category": "other",
                    "default_amount": amount or 0,
                    "currency_id": self.env.company.currency_id.id,
                })

            note_text = note or f"Venue booking for {match.name} at {venue_name}"
            event = self.env["federation.finance.event"].create_from_source(
                match, fee_type, amount=amount, event_type="charge", partner=partner, note=note_text
            )
            events |= event

        return events

    def _advance_bracket_teams(self):
        """After a match is done, populate next bracket matches automatically."""
        self.ensure_one()
        if self.home_score == self.away_score:
            return  # draw — no automatic advancement

        next_matches = self.search([
            "|",
            ("source_match_1_id", "=", self.id),
            ("source_match_2_id", "=", self.id),
        ])
        for nm in next_matches:
            if nm.source_match_1_id == self and not nm.home_team_id:
                team = self._get_result_team(nm.source_type_1 or "winner")
                if team:
                    nm.home_team_id = team
            if nm.source_match_2_id == self and not nm.away_team_id:
                team = self._get_result_team(nm.source_type_2 or "winner")
                if team:
                    nm.away_team_id = team