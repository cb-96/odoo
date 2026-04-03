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