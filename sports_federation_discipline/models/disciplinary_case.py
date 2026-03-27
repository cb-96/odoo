from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FederationDisciplinaryCase(models.Model):
    _name = "federation.disciplinary.case"
    _description = "Disciplinary Case"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "opened_on desc, id desc"

    name = fields.Char(required=True, tracking=True)
    reference = fields.Char(
        string="Reference",
        copy=False,
        readonly=True,
        default="New",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("under_review", "Under Review"),
            ("decided", "Decided"),
            ("appealed", "Appealed"),
            ("closed", "Closed"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    opened_on = fields.Date(
        string="Opened On",
        default=fields.Date.context_today,
    )
    decided_on = fields.Date(string="Decided On")
    closed_on = fields.Date(string="Closed On")
    responsible_user_id = fields.Many2one(
        "res.users",
        string="Responsible User",
    )
    incident_ids = fields.One2many(
        "federation.match.incident",
        "case_id",
        string="Incidents",
    )
    sanction_ids = fields.One2many(
        "federation.sanction",
        "case_id",
        string="Sanctions",
    )
    suspension_ids = fields.One2many(
        "federation.suspension",
        "case_id",
        string="Suspensions",
    )
    subject_player_id = fields.Many2one(
        "federation.player",
        string="Subject Player",
        ondelete="set null",
    )
    subject_club_id = fields.Many2one(
        "federation.club",
        string="Subject Club",
        ondelete="set null",
    )
    subject_referee_id = fields.Many2one(
        "federation.referee",
        string="Subject Referee",
        ondelete="set null",
    )
    summary = fields.Text(string="Summary")
    notes = fields.Text(string="Notes")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("reference", "New") == "New":
                vals["reference"] = self.env["ir.sequence"].next_by_code(
                    "federation.disciplinary.case"
                ) or "New"
        return super().create(vals_list)

    @api.constrains(
        "subject_player_id",
        "subject_club_id",
        "subject_referee_id",
        "incident_ids",
    )
    def _check_subject(self):
        for record in self:
            if not any([
                record.subject_player_id,
                record.subject_club_id,
                record.subject_referee_id,
                record.incident_ids,
            ]):
                raise ValidationError(
                    "At least one subject (Player, Club, Referee) "
                    "or incident must be present."
                )

    def action_submit_review(self):
        for record in self:
            record.state = "under_review"
            for incident in record.incident_ids:
                if incident.status == "new":
                    incident.status = "attached"

    def action_decide(self):
        for record in self:
            record.state = "decided"
            record.decided_on = fields.Date.context_today(record)

    def action_mark_appealed(self):
        for record in self:
            record.state = "appealed"

    def action_close(self):
        for record in self:
            record.state = "closed"
            record.closed_on = fields.Date.context_today(record)
            for incident in record.incident_ids:
                if incident.status != "closed":
                    incident.status = "closed"