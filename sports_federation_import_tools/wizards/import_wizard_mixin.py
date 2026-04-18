import base64
import csv
import hashlib
import io

from odoo import fields, models
from odoo.addons.sports_federation_base.models.failure_feedback import DEFAULT_OPERATOR_MESSAGES
from odoo.exceptions import AccessError, ValidationError


class FederationImportWizardMixin(models.AbstractModel):
    _name = "federation.import.wizard.mixin"
    _description = "Federation Import Wizard Mixin"

    upload_file = fields.Binary(string="CSV File", required=True)
    upload_filename = fields.Char(string="Filename")
    dry_run = fields.Boolean(string="Dry Run", default=True)
    template_id = fields.Many2one(
        "federation.import.template",
        string="Import Template",
        default=lambda self: self._default_template_id(),
    )
    governance_job_id = fields.Many2one(
        "federation.import.job",
        string="Governance Job",
        readonly=True,
    )
    integration_delivery_id = fields.Many2one(
        "federation.integration.delivery",
        string="Inbound Delivery",
        readonly=True,
    )
    approval_state = fields.Selection(
        related="governance_job_id.state",
        string="Approval State",
        readonly=True,
    )
    contract_version = fields.Char(
        related="template_id.contract_version",
        string="Contract Version",
        readonly=True,
    )
    mapping_guide = fields.Text(string="Column Guide", compute="_compute_mapping_guide", readonly=True)
    result_message = fields.Text(string="Result", readonly=True)
    verification_summary = fields.Text(
        related="governance_job_id.verification_summary",
        string="Verification Summary",
        readonly=True,
    )
    line_count = fields.Integer(string="Total Lines", readonly=True)
    success_count = fields.Integer(string="Success", readonly=True)
    error_count = fields.Integer(string="Errors", readonly=True)
    preview_file_checksum = fields.Char(readonly=True)

    def _compute_mapping_guide(self):
        """Compute mapping guide."""
        for wizard in self:
            parts = []
            if wizard.template_id:
                parts.append(wizard.template_id.build_mapping_guide())
            custom_guide = wizard._get_mapping_guide()
            if custom_guide:
                parts.append(custom_guide)
            wizard.mapping_guide = "\n\n".join(part for part in parts if part)

    def _default_template_id(self):
        """Handle default template ID."""
        return self.env["federation.import.template"].search(
            [("wizard_model", "=", self._name)],
            limit=1,
        )

    def _get_mapping_guide(self):
        """Return mapping guide."""
        return ""

    def _get_import_target_model(self):
        """Return import target model."""
        return ""

    def _current_upload_checksum(self):
        """Handle current upload checksum."""
        self.ensure_one()
        if not self.upload_file:
            raise ValidationError("Please upload a CSV file.")
        return hashlib.sha256(base64.b64decode(self.upload_file)).hexdigest()

    def _get_target_record_count(self):
        """Return target record count."""
        self.ensure_one()
        target_model = self._get_import_target_model()
        if not target_model:
            return 0
        return self.env[target_model].search_count([])

    def _build_preview_verification_summary(self):
        """Build preview verification summary."""
        self.ensure_one()
        return "\n".join(
            [
                f"Template: {self.template_id.display_name if self.template_id else self._name}",
                f"Contract version: {self.template_id.contract_version if self.template_id else 'n/a'}",
                f"Requested by: {self.env.user.display_name}",
                f"Preview totals: {self.line_count} lines, {self.success_count} successful, {self.error_count} errors",
                f"Current target record count: {self._get_target_record_count()}",
            ]
        )

    def _build_execution_verification_summary(self, baseline_count):
        """Build execution verification summary."""
        self.ensure_one()
        after_count = self._get_target_record_count()
        net_new = after_count - (baseline_count or 0)
        return "\n".join(
            [
                f"Template: {self.template_id.display_name if self.template_id else self._name}",
                f"Executed by: {self.env.user.display_name}",
                f"Execution totals: {self.line_count} lines, {self.success_count} successful, {self.error_count} errors",
                f"Target records before import: {baseline_count or 0}",
                f"Target records after import: {after_count}",
                f"Net new target records: {net_new}",
            ]
        )

    def _get_overall_failure_category(self, error_categories=None):
        """Return the top-level category for the latest import result."""
        categories = set((error_categories or {}).keys())
        if not (self.error_count or categories):
            return False
        if "unexpected_error" in categories:
            return "unexpected_bug"
        if self.error_count:
            return "data_validation"
        if categories:
            return "data_validation"
        return "operator_input"

    def _get_overall_operator_message(self, error_categories=None):
        """Return an operator-facing summary for the latest import result."""
        category = self._get_overall_failure_category(error_categories=error_categories)
        if not category:
            return False
        if category == "data_validation":
            return (
                "The import completed with row-level validation errors. Review the categorized result "
                "summary before retrying."
            )
        return DEFAULT_OPERATOR_MESSAGES[category]

    def _ensure_live_import_approved(self):
        """Handle ensure live import approved."""
        self.ensure_one()
        if not self.template_id or not self.template_id.approval_required:
            return
        job = self.governance_job_id
        if not job or job.state != "approved":
            raise ValidationError(
                "Live imports require an approved governance job. Run a dry run, request approval, and approve the job before importing."
            )
        if job.file_checksum != self._current_upload_checksum():
            raise ValidationError(
                "The uploaded CSV has changed since approval. Run a fresh dry run and request approval again."
            )
        if job.template_id != self.template_id:
            raise ValidationError(
                "The selected import template does not match the approved governance job. Request approval again."
            )

    def _prepare_import_execution(self):
        """Prepare import execution."""
        self.ensure_one()
        if self.dry_run:
            return 0
        self._ensure_live_import_approved()
        return self._get_target_record_count()

    def _reopen_wizard(self):
        """Handle reopen wizard."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _finalize_import_result(
        self,
        line_count,
        success_count,
        error_count,
        errors,
        error_categories=None,
        baseline_count=0,
    ):
        """Handle finalize import result."""
        self.ensure_one()
        checksum = self._current_upload_checksum()
        result_message = self._build_result_message(
            line_count,
            success_count,
            error_count,
            errors,
            error_categories=error_categories,
        )
        write_vals = {
            "line_count": line_count,
            "success_count": success_count,
            "error_count": error_count,
            "result_message": result_message,
        }
        if self.dry_run:
            write_vals["preview_file_checksum"] = checksum
            if self.governance_job_id and (
                self.governance_job_id.file_checksum != checksum
                or self.governance_job_id.template_id != self.template_id
            ):
                write_vals["governance_job_id"] = False
        self.write(write_vals)

        if self.integration_delivery_id and self.dry_run:
            self.integration_delivery_id.action_mark_previewed(self)

        if not self.dry_run and self.governance_job_id and self.governance_job_id.state == "approved":
            after_count = self._get_target_record_count()
            failure_category = self._get_overall_failure_category(error_categories=error_categories)
            operator_message = self._get_overall_operator_message(error_categories=error_categories)
            self.governance_job_id.write(
                {
                    "state": "completed" if not error_count else "completed_with_errors",
                    "line_count": line_count,
                    "success_count": success_count,
                    "error_count": error_count,
                    "failure_category": failure_category,
                    "operator_message": operator_message,
                    "execution_result_message": result_message,
                    "verification_summary": self._build_execution_verification_summary(baseline_count),
                    "pre_import_record_count": baseline_count,
                    "post_import_record_count": after_count,
                    "executed_by_id": self.env.user.id,
                    "executed_on": fields.Datetime.now(),
                }
            )
            if self.integration_delivery_id:
                self.integration_delivery_id.action_mark_processed(self.governance_job_id)
        return self._reopen_wizard()

    def action_request_approval(self):
        """Execute the request approval action."""
        self.ensure_one()
        if not self.template_id:
            raise ValidationError("Select an import template before requesting approval.")
        current_checksum = self._current_upload_checksum()
        if not self.preview_file_checksum or self.preview_file_checksum != current_checksum:
            raise ValidationError(
                "Run a dry-run preview for the current CSV before requesting approval."
            )
        if not self.line_count:
            raise ValidationError("Run a dry-run preview before requesting approval.")

        columns = self._get_csv_reader().fieldnames or []
        job = self.env["federation.import.job"].create(
            {
                "template_id": self.template_id.id,
                "wizard_model": self._name,
                "target_model": self._get_import_target_model(),
                "state": "draft",
                "contract_name": self.template_id.code or self._name,
                "schema_version": self.template_id.contract_version or "csv_v1",
                "integration_delivery_id": self.integration_delivery_id.id,
                "upload_filename": self.upload_filename,
                "file_checksum": current_checksum,
                "column_names": ", ".join(columns),
                "line_count": self.line_count,
                "success_count": self.success_count,
                "error_count": self.error_count,
                "failure_category": self._get_overall_failure_category(),
                "operator_message": self._get_overall_operator_message(),
                "preview_result_message": self.result_message,
                "verification_summary": self._build_preview_verification_summary(),
            }
        )
        job.action_submit_for_approval()
        self.governance_job_id = job
        return self._reopen_wizard()

    def action_approve_import(self):
        """Execute the approve import action."""
        self.ensure_one()
        if not self.env.user.has_group("sports_federation_base.group_federation_manager"):
            raise AccessError("Only federation managers can approve import jobs.")
        if not self.governance_job_id:
            raise ValidationError("Request approval before approving an import job.")
        if self.governance_job_id.file_checksum != self._current_upload_checksum():
            raise ValidationError(
                "The uploaded CSV has changed since the approval request. Run a new dry run and request approval again."
            )
        self.governance_job_id.action_approve()
        return self._reopen_wizard()

    def action_view_governance_job(self):
        """Execute the view governance job action."""
        self.ensure_one()
        if not self.governance_job_id:
            raise ValidationError("No governance job is linked to this import yet.")
        return {
            "type": "ir.actions.act_window",
            "name": "Import Governance Job",
            "res_model": "federation.import.job",
            "res_id": self.governance_job_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def _get_csv_reader(self):
        """Return CSV reader."""
        self.ensure_one()
        if not self.upload_file:
            raise ValidationError("Please upload a CSV file.")

        content = base64.b64decode(self.upload_file)
        content_str = content.decode("utf-8-sig")
        sample = content_str[:2048]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;")
        except csv.Error:
            dialect = csv.excel

        reader = csv.DictReader(io.StringIO(content_str), dialect=dialect)
        if not reader.fieldnames:
            raise ValidationError("CSV file is empty or invalid.")
        reader.fieldnames = [field.strip() if field else field for field in reader.fieldnames]
        return reader

    def _require_columns(self, fieldnames, required_columns):
        """Handle require columns."""
        missing = [column for column in required_columns if column not in fieldnames]
        if missing:
            raise ValidationError(f"Missing required columns: {', '.join(missing)}")

    def _get_row_value(self, row, *candidates):
        """Return row value."""
        for candidate in candidates:
            value = row.get(candidate)
            if value not in (None, False):
                stripped = value.strip()
                if stripped:
                    return stripped
        return ""

    def _record_error(self, errors, error_categories, row_num, category, message):
        """Record error."""
        errors.append(f"Row {row_num} [{category}]: {message}")
        error_categories[category] = error_categories.get(category, 0) + 1

    def _categorize_exception(self, error):
        """Handle categorize exception."""
        message = str(error)
        lowered = message.lower()
        if "not found" in lowered:
            return "missing_reference", message
        if "already exists" in lowered or "unique" in lowered:
            return "duplicate_entry", message
        if "eligible" in lowered:
            return "ineligible_participant", message
        if "format" in lowered or "invalid" in lowered:
            return "format_error", message
        if "required" in lowered:
            return "missing_required_field", message
        if isinstance(error, ValidationError):
            return "constraint_violation", message
        return "unexpected_error", message

    def _execute_row_create(self, row_num, create_row, errors, error_categories):
        """Execute one row-level create callback and record shared failures."""
        if self.dry_run:
            return True
        try:
            create_row()
            return True
        except Exception as error:
            category, message = self._categorize_exception(error)
            self._record_error(errors, error_categories, row_num, category, message)
            return False

    def _build_result_message(self, line_count, success_count, error_count, errors, error_categories=None):
        """Build result message."""
        result_parts = [
            f"Total lines processed: {line_count}",
            f"Successful: {success_count}",
            f"Errors: {error_count}",
        ]

        if self.dry_run:
            result_parts.append("\n*** DRY RUN - No records were created ***")

        if error_categories:
            result_parts.append("\nError categories:")
            for category, count in sorted(error_categories.items()):
                result_parts.append(f"- {category}: {count}")

        if errors:
            result_parts.append("\nErrors:")
            result_parts.extend(errors)

        return "\n".join(result_parts)