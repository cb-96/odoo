from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RoundRobinWizard(models.TransientModel):
    _name = "federation.round.robin.wizard"
    _description = "Generate Round-Robin Schedule"

    tournament_id = fields.Many2one(
        "federation.tournament", string="Tournament", required=True
    )
    stage_id = fields.Many2one(
        "federation.tournament.stage", string="Stage", required=True,
        domain="[('tournament_id', '=', tournament_id)]"
    )
    group_id = fields.Many2one(
        "federation.tournament.group", string="Group",
        domain="[('stage_id', '=', stage_id)]"
    )
    participant_ids = fields.Many2many(
        "federation.tournament.participant", string="Participants"
    )
    use_all_participants = fields.Boolean(string="Use All Registered", default=True)
    round_type = fields.Selection(
        [("single", "Single Round"), ("double", "Double Round")],
        string="Round Type", default="single", required=True
    )
    start_datetime = fields.Datetime(string="Start Date/Time")
    interval_hours = fields.Integer(string="Interval (hours)", default=2)
    venue = fields.Char(string="Default Venue")
    overwrite = fields.Boolean(string="Overwrite Existing")

    summary = fields.Text(string="Summary", compute="_compute_summary", store=False)

    @api.depends("tournament_id", "stage_id", "group_id", "use_all_participants",
                 "participant_ids", "round_type")
    def _compute_summary(self):
        for wiz in self:
            parts = wiz._get_participants()
            n = len(parts)
            if n < 2:
                wiz.summary = "Need at least 2 participants."
                continue
            rounds = n - 1 if n % 2 == 0 else n
            matches_per_round = n // 2
            total = rounds * matches_per_round
            if wiz.round_type == "double":
                total *= 2
            wiz.summary = (
                f"{n} participants, {rounds} rounds, "
                f"{matches_per_round} matches/round, {total} total matches."
            )

    def _get_participants(self):
        self.ensure_one()
        if self.use_all_participants:
            domain = [("tournament_id", "=", self.tournament_id.id), ("state", "=", "confirmed")]
            if self.group_id:
                domain.append(("group_id", "=", self.group_id.id))
            elif self.stage_id:
                domain.append(("stage_id", "=", self.stage_id.id))
            return self.env["federation.tournament.participant"].search(domain)
        return self.participant_ids

    def action_generate(self):
        self.ensure_one()
        participants = self._get_participants()
        if len(participants) < 2:
            raise UserError(_("At least 2 confirmed participants required."))
        options = {
            "double_round": self.round_type == "double",
            "start_datetime": self.start_datetime,
            "interval_hours": self.interval_hours,
            "venue": self.venue or "",
            "overwrite": self.overwrite,
            "group": self.group_id,
        }
        engine = self.env["federation.competition.engine.service"]
        matches = engine.generate_round_robin_schedule(
            self.tournament_id, self.stage_id, participants, options
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Schedule Generated"),
                "message": _("%d matches created.") % len(matches),
                "type": "success",
                "next": {"type": "ir.actions.act_window_close"},
            },
        }