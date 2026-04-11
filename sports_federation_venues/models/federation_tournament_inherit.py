from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class FederationTournament(models.Model):
    _inherit = "federation.tournament"

    venue_id = fields.Many2one(
        "federation.venue",
        string="Venue",
        tracking=True,
    )
    venue_notes = fields.Text(string="Venue Notes")
    planned_gameday_total = fields.Integer(
        string="Planned Gamedays",
        help="How many gameday slots this tournament should have during planning.",
    )
    gameday_ids = fields.One2many(
        "federation.gameday",
        "tournament_id",
        string="Gamedays",
    )
    gameday_count = fields.Integer(
        string="Gamedays",
        compute="_compute_gameday_count",
        store=True,
    )

    @api.depends("gameday_ids")
    def _compute_gameday_count(self):
        for record in self:
            record.gameday_count = len(record.gameday_ids)

    def action_view_gamedays(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "sports_federation_venues.action_federation_gameday"
        )
        action["domain"] = [("tournament_id", "=", self.id)]
        action["context"] = {"default_tournament_id": self.id}
        return action

    def action_generate_planned_gamedays(self):
        self.ensure_one()
        if self.planned_gameday_total < 1:
            raise ValidationError(
                _("Set Planned Gamedays to at least 1 before generating slots.")
            )

        existing_count = len(self.gameday_ids)
        if existing_count >= self.planned_gameday_total:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("No New Gamedays"),
                    "message": _(
                        "This tournament already has %(count)s gamedays, which meets or exceeds the planned total."
                    )
                    % {"count": existing_count},
                    "type": "info",
                },
            }

        next_sequence = max(self.gameday_ids.mapped("sequence") or [0]) + 1
        values = []
        while existing_count + len(values) < self.planned_gameday_total:
            values.append(
                {
                    "tournament_id": self.id,
                    "sequence": next_sequence,
                }
            )
            next_sequence += 1

        created = self.env["federation.gameday"].create(values)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Gamedays Generated"),
                "message": _(
                    "Created %(count)s planned gamedays for %(tournament)s."
                )
                % {
                    "count": len(created),
                    "tournament": self.display_name,
                },
                "type": "success",
            },
        }


class FederationTournamentStage(models.Model):
    _inherit = "federation.tournament.stage"

    gameday_ids = fields.One2many(
        "federation.gameday",
        "stage_id",
        string="Gamedays",
    )
    gameday_count = fields.Integer(
        string="Gamedays",
        compute="_compute_gameday_count",
        store=True,
    )

    @api.depends("gameday_ids")
    def _compute_gameday_count(self):
        for record in self:
            record.gameday_count = len(record.gameday_ids)

    def action_view_gamedays(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "sports_federation_venues.action_federation_gameday"
        )
        action["domain"] = [("stage_id", "=", self.id)]
        action["context"] = {
            "default_tournament_id": self.tournament_id.id,
            "default_stage_id": self.id,
        }
        return action