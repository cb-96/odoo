from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class FederationGameday(models.Model):
    _name = "federation.gameday"
    _description = "Gameday"
    _order = "start_datetime desc, id"

    name = fields.Char(string="Reference", compute="_compute_name", store=True)
    sequence = fields.Integer(string="Sequence")
    tournament_id = fields.Many2one(
        "federation.tournament",
        string="Tournament",
        ondelete="cascade",
    )
    stage_id = fields.Many2one(
        "federation.tournament.stage",
        string="Stage",
        ondelete="set null",
        domain="[('tournament_id', '=', tournament_id)]",
    )
    start_datetime = fields.Datetime(string="Start Date/Time")
    venue_id = fields.Many2one(
        "federation.venue", string="Venue", ondelete="cascade"
    )
    playing_area_id = fields.Many2one(
        "federation.playing.area",
        string="Playing Area",
        domain="[('venue_id', '=', venue_id)]",
    )
    match_ids = fields.One2many("federation.match", "gameday_id", string="Matches")
    match_count = fields.Integer(
        string="Match Count",
        compute="_compute_match_count",
        store=True,
    )

    _tournament_sequence_unique = models.Constraint(
        "unique (tournament_id, sequence)",
        "Gameday sequence must be unique per tournament.",
    )

    @api.depends("start_datetime", "venue_id", "tournament_id", "stage_id", "sequence")
    def _compute_name(self):
        for rec in self:
            if rec.start_datetime and rec.venue_id:
                # store a human-friendly reference
                rec.name = f"{rec.venue_id.name} - {rec.start_datetime}"
            elif rec.tournament_id and rec.sequence:
                if rec.stage_id:
                    rec.name = _(
                        "%(tournament)s - %(stage)s - Gameday %(sequence)s"
                    ) % {
                        "tournament": rec.tournament_id.display_name,
                        "stage": rec.stage_id.display_name,
                        "sequence": rec.sequence,
                    }
                else:
                    rec.name = _(
                        "%(tournament)s - Gameday %(sequence)s"
                    ) % {
                        "tournament": rec.tournament_id.display_name,
                        "sequence": rec.sequence,
                    }
            else:
                rec.name = _("Gameday")

    @api.depends("match_ids")
    def _compute_match_count(self):
        for rec in self:
            rec.match_count = len(rec.match_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            stage_id = vals.get("stage_id")
            tournament_id = vals.get("tournament_id")
            if stage_id and not tournament_id:
                stage = self.env["federation.tournament.stage"].browse(stage_id)
                if stage.exists():
                    vals["tournament_id"] = stage.tournament_id.id
                    tournament_id = stage.tournament_id.id
            if tournament_id and not vals.get("sequence"):
                vals["sequence"] = self._next_tournament_sequence(tournament_id)
        return super().create(vals_list)

    @api.model
    def _next_tournament_sequence(self, tournament_id):
        last = self.search(
            [("tournament_id", "=", tournament_id)],
            order="sequence desc, id desc",
            limit=1,
        )
        return (last.sequence or 0) + 1

    @api.onchange("stage_id")
    def _onchange_stage_id(self):
        if self.stage_id and not self.tournament_id:
            self.tournament_id = self.stage_id.tournament_id

    @api.constrains("sequence", "tournament_id")
    def _check_sequence(self):
        for rec in self:
            if rec.tournament_id and rec.sequence < 1:
                raise ValidationError(
                    _("Tournament gameday sequences must be positive numbers.")
                )

    @api.constrains("stage_id", "tournament_id")
    def _check_stage_tournament_consistency(self):
        for rec in self:
            if rec.stage_id and not rec.tournament_id:
                raise ValidationError(
                    _("Set a tournament before assigning a stage to a gameday.")
                )
            if rec.stage_id and rec.stage_id.tournament_id != rec.tournament_id:
                raise ValidationError(
                    _("The selected stage must belong to the gameday's tournament.")
                )

    @api.model
    def find_or_create(self, venue_id, start_dt, playing_area_id=None):
        """Find a gameday for the given `venue_id` on the date of `start_dt`, or create one.

        This groups matches by venue and calendar day (server timezone).
        """
        if not venue_id or not start_dt:
            return False

        from datetime import timedelta

        # Normalize to the day of start_dt
        day_start = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        domain = [
            ("venue_id", "=", venue_id),
            ("start_datetime", ">=", day_start),
            ("start_datetime", "<", day_end),
        ]
        if playing_area_id:
            domain.append(("playing_area_id", "=", playing_area_id))

        existing = self.search(domain, limit=1)
        if existing:
            return existing

        vals = {
            "start_datetime": start_dt,
            "venue_id": venue_id,
            "playing_area_id": playing_area_id,
        }
        return self.create(vals)
