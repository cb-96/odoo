from odoo import _, api, fields, models
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
        domain="['|', ('tournament_id', '=', False), ('tournament_id', '=', tournament_id)]",
        ondelete="set null",
        tracking=True,
    )

    def _apply_gameday_defaults(self, vals):
        gameday_id = vals.get("gameday_id")
        if not gameday_id:
            return vals

        gameday = self.env["federation.gameday"].browse(gameday_id)
        if not gameday.exists():
            return vals

        if gameday.tournament_id and not vals.get("tournament_id"):
            vals["tournament_id"] = gameday.tournament_id.id
        if gameday.stage_id and not vals.get("stage_id"):
            vals["stage_id"] = gameday.stage_id.id
        if gameday.venue_id and not vals.get("venue_id"):
            vals["venue_id"] = gameday.venue_id.id
        if gameday.playing_area_id and not vals.get("playing_area_id"):
            vals["playing_area_id"] = gameday.playing_area_id.id
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        prepared_vals_list = [
            self._apply_gameday_defaults(dict(vals)) for vals in vals_list
        ]
        return super().create(prepared_vals_list)

    def write(self, vals):
        prepared_vals = self._apply_gameday_defaults(dict(vals))
        return super().write(prepared_vals)

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

    @api.onchange("gameday_id")
    def _onchange_gameday_id(self):
        if not self.gameday_id:
            return
        if self.gameday_id.tournament_id and not self.tournament_id:
            self.tournament_id = self.gameday_id.tournament_id
        if self.gameday_id.stage_id and not self.stage_id:
            self.stage_id = self.gameday_id.stage_id
        if self.gameday_id.venue_id:
            self.venue_id = self.gameday_id.venue_id
        if self.gameday_id.playing_area_id:
            self.playing_area_id = self.gameday_id.playing_area_id

    @api.constrains("gameday_id", "tournament_id", "stage_id", "venue_id")
    def _check_gameday_scope(self):
        for rec in self:
            if not rec.gameday_id:
                continue
            if rec.gameday_id.tournament_id and rec.gameday_id.tournament_id != rec.tournament_id:
                raise ValidationError(
                    _("A match can only use a gameday from the same tournament.")
                )
            if rec.gameday_id.stage_id and rec.gameday_id.stage_id != rec.stage_id:
                raise ValidationError(
                    _("A match can only use a gameday assigned to the same stage.")
                )
            if rec.gameday_id.venue_id and rec.gameday_id.venue_id != rec.venue_id:
                raise ValidationError(
                    _("A match venue must match the selected gameday venue.")
                )

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