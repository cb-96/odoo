from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FederationDocumentSubmission(models.Model):
    _name = "federation.document.submission"
    _description = "Federation Document Submission"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    TARGET_MODEL_SELECTION = [
        ("federation.club", "Club"),
        ("federation.player", "Player"),
        ("federation.referee", "Referee"),
        ("federation.venue", "Venue"),
        ("federation.club.representative", "Club Representative"),
    ]

    STATUS_SELECTION = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("replacement_requested", "Replacement Requested"),
        ("expired", "Expired"),
    ]

    name = fields.Char(string="Name", required=True, tracking=True)
    requirement_id = fields.Many2one(
        "federation.document.requirement",
        string="Requirement",
        required=True,
        ondelete="restrict",
        tracking=True,
        index=True,
    )
    target_model = fields.Selection(
        selection=TARGET_MODEL_SELECTION,
        string="Target Model",
        related="requirement_id.target_model",
        store=True,
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
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )

    attachment_ids = fields.Many2many(
        "ir.attachment",
        string="Attachments",
    )
    issue_date = fields.Date(string="Issue Date", tracking=True)
    expiry_date = fields.Date(string="Expiry Date", tracking=True)
    reviewer_id = fields.Many2one(
        "res.users",
        string="Reviewer",
        tracking=True,
    )
    reviewed_on = fields.Datetime(string="Reviewed On", tracking=True)
    notes = fields.Text(string="Notes")

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

    @api.constrains("requirement_id", "target_model")
    def _check_target_matches_requirement(self):
        """Ensure target matches requirement.target_model."""
        for rec in self:
            if not rec.requirement_id:
                continue
            target_fields_map = {
                "federation.club": rec.club_id,
                "federation.player": rec.player_id,
                "federation.referee": rec.referee_id,
                "federation.venue": rec.venue_id,
                "federation.club.representative": rec.club_representative_id,
            }
            expected_target = target_fields_map.get(rec.requirement_id.target_model)
            if not expected_target:
                raise ValidationError(
                    f"Target entity does not match requirement model "
                    f"'{rec.requirement_id.target_model}'."
                )

    @api.constrains("issue_date", "expiry_date")
    def _check_dates(self):
        """Ensure expiry_date >= issue_date if both are set."""
        for rec in self:
            if rec.issue_date and rec.expiry_date:
                if rec.expiry_date < rec.issue_date:
                    raise ValidationError(
                        "Expiry date cannot be before issue date."
                    )

    @api.constrains("requirement_id", "expiry_date")
    def _check_expiry_date_required(self):
        """Ensure expiry_date is set when requirement requires it."""
        for rec in self:
            if rec.requirement_id and rec.requirement_id.requires_expiry_date:
                if not rec.expiry_date:
                    raise ValidationError(
                        f"Expiry date is required for requirement '{rec.requirement_id.name}'."
                    )

    def is_expired(self):
        """Check if submission is expired based on expiry_date."""
        self.ensure_one()
        if not self.expiry_date:
            return False
        return self.expiry_date < fields.Date.context_today(self)

    def action_submit(self):
        """Submit the document for review."""
        for rec in self:
            if rec.status != "draft":
                raise ValidationError("Only draft documents can be submitted.")
            rec.status = "submitted"

    def action_approve(self):
        """Approve the submitted document."""
        for rec in self:
            if rec.status not in ("submitted", "replacement_requested"):
                raise ValidationError(
                    "Only submitted or replacement requested documents can be approved."
                )
            rec.write({
                "status": "approved",
                "reviewer_id": self.env.user.id,
                "reviewed_on": fields.Datetime.now(),
            })

    def action_reject(self):
        """Reject the submitted document."""
        for rec in self:
            if rec.status not in ("submitted", "replacement_requested"):
                raise ValidationError(
                    "Only submitted or replacement requested documents can be rejected."
                )
            rec.write({
                "status": "rejected",
                "reviewer_id": self.env.user.id,
                "reviewed_on": fields.Datetime.now(),
            })

    def action_request_replacement(self):
        """Request a replacement document."""
        for rec in self:
            if rec.status != "approved":
                raise ValidationError(
                    "Only approved documents can have replacement requested."
                )
            rec.write({
                "status": "replacement_requested",
                "reviewer_id": self.env.user.id,
                "reviewed_on": fields.Datetime.now(),
            })

    def action_reset_to_draft(self):
        """Reset to draft status."""
        for rec in self:
            rec.status = "draft"