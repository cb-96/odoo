from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FederationMatch(models.Model):
    _inherit = "federation.match"

    venue_id = fields.Many2one(
        "federation.venue",
        string="Venue",
        tracking=True,
    )
    playing_area_id = fields.Many2one(
        "federation.playing.area",
        string="Playing Area",
        domain="[('venue_id', '=', venue_id)]",
        tracking=True,
    )
    gameday_id = fields.Many2one(
        "federation.gameday",
        string="Gameday",
        domain="[('venue_id', '=', venue_id)]",
        ondelete="set null",
        tracking=True,
    )

    @api.constrains("venue_id", "playing_area_id")
    def _check_playing_area_venue(self):
        for rec in self:
            if rec.playing_area_id and rec.venue_id:
                if rec.playing_area_id.venue_id != rec.venue_id:
                    raise ValidationError(
                        "The playing area must belong to the selected venue."
                    )

    @api.onchange("playing_area_id")
    def _onchange_playing_area_id(self):
        if self.playing_area_id and not self.venue_id:
            self.venue_id = self.playing_area_id.venue_id

    @api.constrains("gameday_id", "home_team_id", "away_team_id")
    def _check_no_duplicate_pairings_on_gameday(self):
        for rec in self:
            if not rec.gameday_id or not rec.home_team_id or not rec.away_team_id:
                continue
            # Only enforce when teams belong to the same category
            if rec.home_team_id.category != rec.away_team_id.category:
                continue
            domain = [
                ("gameday_id", "=", rec.gameday_id.id),
                "|",
                "&", ("home_team_id", "=", rec.home_team_id.id), ("away_team_id", "=", rec.away_team_id.id),
                "&", ("home_team_id", "=", rec.away_team_id.id), ("away_team_id", "=", rec.home_team_id.id),
                ("id", "!=", rec.id),
            ]
            dup = self.search(domain, limit=1)
            if dup:
                raise ValidationError(
                    "Teams in the same category cannot play the same opponent more than once on the same gameday."
                )