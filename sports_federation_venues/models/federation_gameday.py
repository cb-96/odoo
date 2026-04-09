from odoo import api, fields, models


class FederationGameday(models.Model):
    _name = "federation.gameday"
    _description = "Gameday"
    _order = "start_datetime desc, id"

    name = fields.Char(string="Reference", compute="_compute_name", store=True)
    start_datetime = fields.Datetime(string="Start Date/Time", required=True)
    venue_id = fields.Many2one(
        "federation.venue", string="Venue", required=True, ondelete="cascade"
    )
    playing_area_id = fields.Many2one(
        "federation.playing.area",
        string="Playing Area",
        domain="[('venue_id', '=', venue_id)]",
    )
    match_ids = fields.One2many("federation.match", "gameday_id", string="Matches")

    @api.depends("start_datetime", "venue_id")
    def _compute_name(self):
        for rec in self:
            if rec.start_datetime and rec.venue_id:
                # store a human-friendly reference
                rec.name = f"{rec.venue_id.name} - {rec.start_datetime}"
            else:
                rec.name = "Gameday"

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
