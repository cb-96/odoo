from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FederationComplianceCheck(models.Model):
    _name = "federation.compliance.check"
    _description = "Federation Compliance Check"
    _order = "create_date desc"

    TARGET_MODEL_SELECTION = [
        ("federation.club", "Club"),
        ("federation.player", "Player"),
        ("federation.referee", "Referee"),
        ("federation.venue", "Venue"),
        ("federation.club.representative", "Club Representative"),
    ]

    STATUS_SELECTION = [
        ("compliant", "Compliant"),
        ("missing", "Missing"),
        ("pending", "Pending"),
        ("expired", "Expired"),
        ("non_compliant", "Non Compliant"),
    ]

    name = fields.Char(string="Name", required=True)
    target_model = fields.Selection(
        selection=TARGET_MODEL_SELECTION,
        string="Target Model",
        required=True,
    )

    # Target entity fields - exactly one must be set
    club_id = fields.Many2one(
        "federation.club",
        string="Club",
        ondelete="cascade",
        index=True,
    )
    player_id = fields.Many2one(
        "federation.player",
        string="Player",
        ondelete="cascade",
        index=True,
    )
    referee_id = fields.Many2one(
        "federation.referee",
        string="Referee",
        ondelete="cascade",
        index=True,
    )
    venue_id = fields.Many2one(
        "federation.venue",
        string="Venue",
        ondelete="cascade",
        index=True,
    )
    club_representative_id = fields.Many2one(
        "federation.club.representative",
        string="Club Representative",
        ondelete="cascade",
        index=True,
    )

    status = fields.Selection(
        selection=STATUS_SELECTION,
        string="Status",
        required=True,
    )
    requirement_id = fields.Many2one(
        "federation.document.requirement",
        string="Requirement",
        required=True,
    )
    submission_id = fields.Many2one(
        "federation.document.submission",
        string="Submission",
    )
    checked_on = fields.Datetime(string="Checked On")
    note = fields.Char(string="Note")

    # Computed field for display
    target_display = fields.Char(
        string="Target",
        compute="_compute_target_display",
        store=True,
    )

    @api.depends(
        "club_id",
        "player_id",
        "referee_id",
        "venue_id",
        "club_representative_id",
    )
    def _compute_target_display(self):
        for rec in self:
            if rec.club_id:
                rec.target_display = rec.club_id.name
            elif rec.player_id:
                rec.target_display = rec.player_id.name
            elif rec.referee_id:
                rec.target_display = rec.referee_id.name
            elif rec.venue_id:
                rec.target_display = rec.venue_id.name
            elif rec.club_representative_id:
                rec.target_display = rec.club_representative_id.display_name
            else:
                rec.target_display = "Not set"

    @api.constrains(
        "club_id",
        "player_id",
        "referee_id",
        "venue_id",
        "club_representative_id",
    )
    def _check_single_target(self):
        """Ensure exactly one target field is set."""
        for rec in self:
            target_fields = [
                rec.club_id,
                rec.player_id,
                rec.referee_id,
                rec.venue_id,
                rec.club_representative_id,
            ]
            set_count = sum(1 for f in target_fields if f)
            if set_count == 0:
                raise ValidationError(
                    "Exactly one target entity must be set."
                )
            if set_count > 1:
                raise ValidationError(
                    "Only one target entity can be set. Multiple targets found."
                )

    @api.constrains("target_model", "club_id", "player_id", "referee_id",
                     "venue_id", "club_representative_id")
    def _check_target_matches_model(self):
        """Ensure target matches target_model."""
        for rec in self:
            target_fields_map = {
                "federation.club": rec.club_id,
                "federation.player": rec.player_id,
                "federation.referee": rec.referee_id,
                "federation.venue": rec.venue_id,
                "federation.club.representative": rec.club_representative_id,
            }
            expected_target = target_fields_map.get(rec.target_model)
            if not expected_target:
                raise ValidationError(
                    f"Target entity does not match target model '{rec.target_model}'."
                )

    @api.model
    def _get_target_field_value(self, record, target_model):
        """Get the target field value for a given record and target model."""
        target_fields_map = {
            "federation.club": record.club_id,
            "federation.player": record.player_id,
            "federation.referee": record.referee_id,
            "federation.venue": record.venue_id,
            "federation.club.representative": record.club_representative_id,
        }
        return target_fields_map.get(target_model)

    @api.model
    def recompute_checks_for_target(self, target_record, target_model):
        """Recompute compliance checks for a specific target record.

        Args:
            target_record: The actual record (club, player, etc.)
            target_model: The model name (e.g., 'federation.club')

        Returns:
            List of created/updated compliance.check records
        """
        # Find applicable requirements for this target model
        requirements = self.env["federation.document.requirement"].search([
            ("target_model", "=", target_model),
            ("active", "=", True),
        ])

        if not requirements:
            return []

        today = fields.Date.context_today(self)
        checks = []

        for requirement in requirements:
            # Find existing submission for this requirement and target
            domain = [
                ("requirement_id", "=", requirement.id),
            ]
            # Add target field filter
            target_field_map = {
                "federation.club": "club_id",
                "federation.player": "player_id",
                "federation.referee": "referee_id",
                "federation.venue": "venue_id",
                "federation.club.representative": "club_representative_id",
            }
            field_name = target_field_map.get(target_model)
            if field_name:
                domain.append((field_name, "=", target_record.id))

            submission = self.env["federation.document.submission"].search(
                domain, limit=1, order="create_date desc"
            )

            # Determine status
            if not submission:
                status = "missing"
                note = "No submission found"
            elif submission.status == "draft":
                status = "pending"
                note = "Submission is in draft"
            elif submission.status == "submitted":
                status = "pending"
                note = "Submission is pending review"
            elif submission.status == "rejected":
                status = "non_compliant"
                note = "Submission was rejected"
            elif submission.status == "replacement_requested":
                status = "pending"
                note = "Replacement requested"
            elif submission.status == "approved":
                # Check if expired
                if submission.expiry_date and submission.expiry_date < today:
                    status = "expired"
                    note = "Document has expired"
                else:
                    status = "compliant"
                    note = "Document is valid"
            else:
                status = "non_compliant"
                note = f"Unknown submission status: {submission.status}"

            # Find or create check record
            check_domain = [
                ("requirement_id", "=", requirement.id),
                (field_name, "=", target_record.id),
            ] if field_name else [("requirement_id", "=", requirement.id)]

            check = self.search(check_domain, limit=1)

            check_values = {
                "name": f"{requirement.name} - {target_record.name}",
                "target_model": target_model,
                "status": status,
                "requirement_id": requirement.id,
                "submission_id": submission.id if submission else False,
                "checked_on": fields.Datetime.now(),
                "note": note,
            }
            # Set target field
            if field_name:
                check_values[field_name] = target_record.id

            if check:
                check.write(check_values)
            else:
                check = self.create(check_values)

            checks.append(check)

        return checks

    def action_recheck(self):
        """Recheck this compliance check."""
        for rec in self:
            target_record = rec._get_target_field_value(rec, rec.target_model)
            if target_record:
                rec.recompute_checks_for_target(target_record, rec.target_model)