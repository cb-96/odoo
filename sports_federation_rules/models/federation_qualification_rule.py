from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FederationQualificationRule(models.Model):
    _name = "federation.qualification.rule"
    _description = "Federation Qualification Rule"
    _order = "rule_set_id, sequence, id"

    rule_set_id = fields.Many2one(
        "federation.rule.set",
        string="Rule Set",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(string="Sequence", default=10, required=True)
    name = fields.Char(string="Rule Name", required=True)
    qualification_type = fields.Selection(
        [
            ("top_n", "Top N Teams Qualify"),
            ("top_percent", "Top Percentage Qualifies"),
            ("min_points", "Minimum Points Required"),
            ("min_position", "Minimum Position Required"),
            ("group_winner", "Group Winners"),
            ("group_runner_up", "Group Runners-Up"),
            ("custom", "Custom Rule"),
        ],
        string="Qualification Type",
        required=True,
    )
    description = fields.Text(
        string="Description",
        help="Detailed description of this qualification rule.",
    )
    value_integer = fields.Integer(
        string="Integer Value",
        help="Numeric value for top-N, min-points, or min-position rules.",
    )
    value_percent = fields.Float(
        string="Percentage Value",
        help="Percentage value for top-percentage rules.",
    )
    target_stage_id = fields.Many2one(
        "federation.tournament.stage",
        string="Target Stage",
        ondelete="set null",
        help="The stage that qualified teams advance to. Extension point for later.",
    )
    active = fields.Boolean(default=True)