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
        "federation.tournament.participant",
        relation="fed_rr_wiz_participant_rel",
        string="Participants",
    )
    use_all_participants = fields.Boolean(
        string="Use All Confirmed Participants", default=True
    )
    round_type = fields.Selection(
        [("single", "Single Round"), ("double", "Double Round")],
        string="Round Type", default="single", required=True
    )
    rounds_count = fields.Integer(string="Full Cycles (repeats)", default=1)
    schedule_by_round = fields.Boolean(string="Schedule By Round", default=False)
    round_interval_hours = fields.Integer(string="Round Interval (hours)", default=24)
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
                wiz.summary = wiz._get_participant_requirement_message(parts)
                continue
            invalid_participants = parts.filtered(lambda participant: participant.state != "confirmed")
            if invalid_participants:
                wiz.summary = wiz._get_participant_requirement_message(parts)
                continue
            rounds = n - 1 if n % 2 == 0 else n
            matches_per_round = n // 2
            per_cycle = rounds * matches_per_round
            if wiz.round_type == "double":
                per_cycle *= 2
            total = per_cycle * (wiz.rounds_count or 1)
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

    def _get_participant_scope_domain(self):
        self.ensure_one()
        domain = [("tournament_id", "=", self.tournament_id.id)]
        if self.group_id:
            domain.append(("group_id", "=", self.group_id.id))
        elif self.stage_id:
            domain.append(("stage_id", "=", self.stage_id.id))
        return domain

    def _get_participant_requirement_message(self, participants):
        self.ensure_one()
        Participant = self.env["federation.tournament.participant"]
        scope_domain = self._get_participant_scope_domain()
        scope_total = Participant.search_count(scope_domain)
        scope_confirmed = Participant.search_count(scope_domain + [("state", "=", "confirmed")])
        tournament_confirmed = Participant.search_count(
            [("tournament_id", "=", self.tournament_id.id), ("state", "=", "confirmed")]
        )

        if not self.use_all_participants:
            selected_total = len(self.participant_ids)
            selected_confirmed = len(
                self.participant_ids.filtered(lambda participant: participant.state == "confirmed")
            )
            if selected_total < 2:
                return _(
                    "Need at least 2 selected participants. Only %(selected)s selected."
                ) % {"selected": selected_total}
            return _(
                "Only confirmed participants can be generated. %(confirmed)s of %(selected)s selected participants are confirmed."
            ) % {
                "confirmed": selected_confirmed,
                "selected": selected_total,
            }

        return _(
            "Need at least 2 confirmed participants in the selected stage or group. Found %(scope_confirmed)s confirmed in scope, %(scope_total)s participant records in scope, and %(tournament_confirmed)s confirmed across the tournament. Confirm the linked tournament participants and make sure they are assigned to this stage or group."
        ) % {
            "scope_confirmed": scope_confirmed,
            "scope_total": scope_total,
            "tournament_confirmed": tournament_confirmed,
        }

    def action_generate(self):
        self.ensure_one()
        participants = self._get_participants()
        self._validate_generation_request(participants)
        options = {
            "double_round": self.round_type == "double",
            "start_datetime": self.start_datetime,
            "interval_hours": self.interval_hours,
            "rounds_count": self.rounds_count,
            "schedule_by_round": self.schedule_by_round,
            "round_interval_hours": self.round_interval_hours,
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

    def _validate_generation_request(self, participants):
        if self.tournament_id.state not in ("open", "in_progress"):
            raise UserError(_("Tournament must be Open or In Progress to generate matches."))

        if not self.tournament_id._get_effective_rule_set():
            raise UserError(_("Assign a rule set before generating a round-robin schedule."))

        if self.stage_id.tournament_id != self.tournament_id:
            raise UserError(_("The selected stage must belong to the selected tournament."))

        if self.group_id and self.group_id.stage_id != self.stage_id:
            raise UserError(_("The selected group must belong to the selected stage."))

        if len(participants) < 2:
            raise UserError(self._get_participant_requirement_message(participants))

        invalid_participants = participants.filtered(lambda participant: participant.state != "confirmed")
        if invalid_participants:
            raise UserError(self._get_participant_requirement_message(participants))