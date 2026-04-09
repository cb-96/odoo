from odoo import api, fields, models


class FederationDocumentRequirement(models.Model):
    _name = "federation.document.requirement"
    _description = "Federation Document Requirement"
    _order = "target_model, name"

    TARGET_MODEL_SELECTION = [
        ("federation.club", "Club"),
        ("federation.player", "Player"),
        ("federation.referee", "Referee"),
        ("federation.venue", "Venue"),
        ("federation.club.representative", "Club Representative"),
    ]

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code", required=True)
    target_model = fields.Selection(
        selection=TARGET_MODEL_SELECTION,
        string="Target Model",
        required=True,
    )
    required_for_all = fields.Boolean(
        string="Required for All",
        default=True,
        help="If checked, this requirement applies to all records of the target model.",
    )
    active = fields.Boolean(default=True)
    description = fields.Text(string="Description")
    requires_expiry_date = fields.Boolean(
        string="Requires Expiry Date",
        default=False,
    )
    validity_days = fields.Integer(
        string="Validity (Days)",
        help="Number of days the document is valid after issue date.",
    )

    _code_target_model_unique = models.Constraint(
        'UNIQUE(code, target_model)',
        'A requirement with this code already exists for this target model.',
    )