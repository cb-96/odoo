from odoo import fields, models


class FederationTournamentInherit(models.Model):
    _inherit = "federation.tournament"

    progression_ids = fields.One2many(
        "federation.stage.progression",
        "tournament_id",
        string="Progression Rules",
    )
    template_id = fields.Many2one(
        "federation.tournament.template",
        string="Template",
        ondelete="set null",
    )

    def action_apply_template(self):
        """Execute the apply template action."""
        self.ensure_one()
        if self.template_id:
            self.template_id.action_apply(self)
