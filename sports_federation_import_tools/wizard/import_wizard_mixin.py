import base64
import csv
import io

from odoo import fields, models
from odoo.exceptions import ValidationError


class FederationImportWizardMixin(models.AbstractModel):
    _name = "federation.import.wizard.mixin"
    _description = "Federation Import Wizard Mixin"

    upload_file = fields.Binary(string="CSV File", required=True)
    upload_filename = fields.Char(string="Filename")
    dry_run = fields.Boolean(string="Dry Run", default=True)
    mapping_guide = fields.Text(string="Column Guide", compute="_compute_mapping_guide", readonly=True)
    result_message = fields.Text(string="Result", readonly=True)
    line_count = fields.Integer(string="Total Lines", readonly=True)
    success_count = fields.Integer(string="Success", readonly=True)
    error_count = fields.Integer(string="Errors", readonly=True)

    def _compute_mapping_guide(self):
        for wizard in self:
            wizard.mapping_guide = wizard._get_mapping_guide()

    def _get_mapping_guide(self):
        return ""

    def _get_csv_reader(self):
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
        missing = [column for column in required_columns if column not in fieldnames]
        if missing:
            raise ValidationError(f"Missing required columns: {', '.join(missing)}")

    def _get_row_value(self, row, *candidates):
        for candidate in candidates:
            value = row.get(candidate)
            if value not in (None, False):
                stripped = value.strip()
                if stripped:
                    return stripped
        return ""

    def _record_error(self, errors, error_categories, row_num, category, message):
        errors.append(f"Row {row_num} [{category}]: {message}")
        error_categories[category] = error_categories.get(category, 0) + 1

    def _categorize_exception(self, error):
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

    def _build_result_message(self, line_count, success_count, error_count, errors, error_categories=None):
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