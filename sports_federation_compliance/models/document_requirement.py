from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError


class FederationDocumentRequirement(models.Model):
    _name = "federation.document.requirement"
    _description = "Federation Document Requirement"
    _order = "target_model, name"

    PORTAL_TARGET_MODELS = {
        "federation.club",
        "federation.referee",
        "federation.club.representative",
    }
    PORTAL_RENEWAL_WARNING_DAYS = 30

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

    @api.model
    def _portal_target_field_map(self):
        return {
            "federation.club": "club_id",
            "federation.player": "player_id",
            "federation.referee": "referee_id",
            "federation.venue": "venue_id",
            "federation.club.representative": "club_representative_id",
        }

    @api.model
    def _portal_get_target_field_name(self, target_model):
        return self._portal_target_field_map().get(target_model)

    @api.model
    def _portal_has_access(self, user=None):
        user = user or self.env.user
        return any(
            bool(self._portal_get_targets_for_user(target_model, user=user))
            for target_model in self.PORTAL_TARGET_MODELS
        )

    @api.model
    def _portal_get_targets_for_user(self, target_model, user=None):
        user = user or self.env.user
        ClubRepresentative = self.env["federation.club.representative"]

        if target_model == "federation.club":
            return ClubRepresentative._get_club_scope_for_user(user=user)
        if target_model == "federation.referee":
            return self.env["federation.referee"]._portal_get_for_user(user=user)
        if target_model == "federation.club.representative":
            return ClubRepresentative.search(
                [
                    ("user_id", "=", user.id),
                    ("is_current", "=", True),
                ]
            )
        return self.env["federation.club"].browse([])

    @api.model
    def _portal_assert_target_access(self, requirement, target_record, user=None):
        user = user or self.env.user
        if requirement.target_model not in self.PORTAL_TARGET_MODELS:
            raise AccessError("This compliance target is not available in the portal.")

        visible_targets = self._portal_get_targets_for_user(
            requirement.target_model,
            user=user,
        )
        if target_record not in visible_targets:
            raise AccessError("You can only manage compliance items that belong to you or your club.")
        return True

    def _portal_get_latest_submission(self, target_record):
        self.ensure_one()
        field_name = self._portal_get_target_field_name(self.target_model)
        if not field_name:
            return self.env["federation.document.submission"].browse([])
        return self.env["federation.document.submission"].sudo().search(
            [
                ("requirement_id", "=", self.id),
                (field_name, "=", target_record.id),
            ],
            limit=1,
            order="create_date desc, id desc",
        )

    def _portal_get_submission_history(self, target_record):
        self.ensure_one()
        field_name = self._portal_get_target_field_name(self.target_model)
        if not field_name:
            return self.env["federation.document.submission"].browse([])
        return self.env["federation.document.submission"].sudo().search(
            [
                ("requirement_id", "=", self.id),
                (field_name, "=", target_record.id),
            ],
            order="create_date desc, id desc",
        )

    def _portal_get_remediation_row(self, submission):
        self.ensure_one()
        if not submission:
            return False

        RemediationReport = self.env.get("federation.report.compliance.remediation")
        if RemediationReport is None:
            return False
        return RemediationReport.sudo().search(
            [("submission_id", "=", submission.id)],
            limit=1,
        )

    def _portal_get_workspace_entry(self, target_record, user=None):
        self.ensure_one()
        self._portal_assert_target_access(self, target_record, user=user)

        today = fields.Date.context_today(self)
        latest_submission = self._portal_get_latest_submission(target_record)
        submission_history = self._portal_get_submission_history(target_record)
        remediation_row = self._portal_get_remediation_row(latest_submission)
        effective_status = (
            latest_submission._portal_get_effective_status()
            if latest_submission
            else "missing"
        )
        status_meta = self.env[
            "federation.document.submission"
        ]._portal_get_status_metadata(
            effective_status,
            latest_submission=latest_submission,
        )

        renewal_due_date = latest_submission.expiry_date if latest_submission else False
        renewal_due_soon = bool(
            renewal_due_date
            and renewal_due_date <= today + timedelta(days=self.PORTAL_RENEWAL_WARNING_DAYS)
            and renewal_due_date >= today
        )
        requires_attention = effective_status in {
            "missing",
            "draft",
            "submitted",
            "rejected",
            "replacement_requested",
            "expired",
        } or renewal_due_soon

        summary_parts = []
        if remediation_row and remediation_row.remediation_note:
            summary_parts.append(remediation_row.remediation_note)
        elif effective_status == "missing":
            summary_parts.append("No submission is on file yet.")
        elif effective_status == "draft":
            summary_parts.append("A draft exists but has not been submitted for review.")
        elif effective_status == "submitted":
            summary_parts.append("Your latest submission is waiting for federation review.")
        elif effective_status == "rejected":
            summary_parts.append("The last submission was rejected and needs replacement documentation.")
        elif effective_status == "replacement_requested":
            summary_parts.append("Federation staff requested updated documentation.")
        elif effective_status == "expired":
            summary_parts.append("The approved document has expired and needs renewal.")
        else:
            summary_parts.append("The latest submission is approved and currently compliant.")

        if renewal_due_date:
            if renewal_due_date < today:
                summary_parts.append(
                    f"Renewal deadline passed on {fields.Date.to_string(renewal_due_date)}."
                )
            elif renewal_due_soon:
                summary_parts.append(
                    f"Renewal is due by {fields.Date.to_string(renewal_due_date)}."
                )
            else:
                summary_parts.append(
                    f"Current approval remains valid until {fields.Date.to_string(renewal_due_date)}."
                )

        detail_url = "/my/compliance/%s/%s/%s" % (
            self.id,
            self.target_model,
            target_record.id,
        )
        return {
            "requirement": self,
            "target": target_record,
            "target_model": self.target_model,
            "target_field_name": self._portal_get_target_field_name(self.target_model),
            "target_label": dict(self.TARGET_MODEL_SELECTION).get(self.target_model),
            "latest_submission": latest_submission,
            "submission_history": submission_history,
            "remediation_row": remediation_row,
            "status_key": effective_status,
            "status_label": status_meta["label"],
            "status_tone": status_meta["tone"],
            "status_summary": " ".join(summary_parts),
            "renewal_due_date": renewal_due_date,
            "renewal_due_soon": renewal_due_soon,
            "requires_attention": requires_attention,
            "can_submit": not latest_submission or latest_submission.status != "submitted",
            "detail_url": detail_url,
        }

    @api.model
    def _portal_get_workspace_entry_for_user(
        self,
        requirement_id,
        target_model,
        target_id,
        user=None,
    ):
        user = user or self.env.user
        requirement = self.sudo().browse(requirement_id)
        if not requirement.exists() or requirement.target_model != target_model:
            return False

        target_record = requirement._portal_get_targets_for_user(
            target_model,
            user=user,
        ).filtered(lambda record: record.id == target_id)[:1]
        if not target_record:
            return False
        return requirement._portal_get_workspace_entry(target_record, user=user)

    @api.model
    def _portal_get_workspace_entries(self, user=None):
        user = user or self.env.user
        entries = []
        requirements = self.sudo().search(
            [
                ("active", "=", True),
                ("target_model", "in", list(self.PORTAL_TARGET_MODELS)),
            ],
            order="target_model, name, id",
        )

        for requirement in requirements:
            targets = requirement._portal_get_targets_for_user(
                requirement.target_model,
                user=user,
            )
            for target_record in targets:
                entries.append(requirement._portal_get_workspace_entry(target_record, user=user))

        def _sort_key(entry):
            renewal_due_date = entry["renewal_due_date"] or fields.Date.to_date("9999-12-31")
            return (
                0 if entry["requires_attention"] else 1,
                renewal_due_date,
                entry["target_label"] or "",
                entry["target"].display_name,
                entry["requirement"].name,
            )

        return sorted(entries, key=_sort_key)