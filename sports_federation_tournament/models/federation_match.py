from odoo import api, fields, models
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
    date_scheduled = fields.Datetime(string="Scheduled Date", tracking=True)
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
            if not match.venue:
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

            note_text = note or f"Venue booking for {match.name} at {match.venue}"
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