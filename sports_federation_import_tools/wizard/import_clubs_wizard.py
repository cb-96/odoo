import base64
import csv
import io

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FederationImportClubsWizard(models.TransientModel):
    _name = "federation.import.clubs.wizard"
    _description = "Import Clubs Wizard"

    upload_file = fields.Binary(string="CSV File", required=True)
    upload_filename = fields.Char(string="Filename")
    dry_run = fields.Boolean(string="Dry Run", default=True)
    result_message = fields.Text(string="Result", readonly=True)
    line_count = fields.Integer(string="Total Lines", readonly=True)
    success_count = fields.Integer(string="Success", readonly=True)
    error_count = fields.Integer(string="Errors", readonly=True)

    def action_parse_and_import(self):
        """Parse CSV and import clubs."""
        self.ensure_one()

        if not self.upload_file:
            raise ValidationError("Please upload a CSV file.")

        # Decode file
        content = base64.b64decode(self.upload_file)
        content_str = content.decode("utf-8-sig")

        # Parse CSV
        reader = csv.DictReader(io.StringIO(content_str))
        required_columns = ["name"]
        if not reader.fieldnames:
            raise ValidationError("CSV file is empty or invalid.")

        missing = [col for col in required_columns if col not in reader.fieldnames]
        if missing:
            raise ValidationError(f"Missing required columns: {', '.join(missing)}")

        # Process rows
        line_count = 0
        success_count = 0
        error_count = 0
        errors = []

        Club = self.env["federation.club"]

        for row_num, row in enumerate(reader, start=2):
            line_count += 1
            name = row.get("name", "").strip()

            if not name:
                errors.append(f"Row {row_num}: Name is required.")
                error_count += 1
                continue

            # Check for duplicate
            existing = Club.search([("name", "=", name)], limit=1)
            if existing:
                errors.append(f"Row {row_num}: Club '{name}' already exists.")
                error_count += 1
                continue

            if not self.dry_run:
                try:
                    Club.create({
                        "name": name,
                        "email": row.get("email", "").strip() or False,
                        "phone": row.get("phone", "").strip() or False,
                        "city": row.get("city", "").strip() or False,
                    })
                    success_count += 1
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
                    error_count += 1
            else:
                success_count += 1

        # Build result message
        result_parts = []
        result_parts.append(f"Total lines processed: {line_count}")
        result_parts.append(f"Successful: {success_count}")
        result_parts.append(f"Errors: {error_count}")

        if self.dry_run:
            result_parts.append("\n*** DRY RUN - No records were created ***")

        if errors:
            result_parts.append("\nErrors:")
            result_parts.extend(errors)

        self.write({
            "line_count": line_count,
            "success_count": success_count,
            "error_count": error_count,
            "result_message": "\n".join(result_parts),
        })

        return {
            "type": "ir.actions.act_window",
            "res_model": "federation.import.clubs.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }