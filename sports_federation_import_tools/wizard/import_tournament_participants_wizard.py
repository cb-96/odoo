import base64
import csv
import io

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class FederationImportTournamentParticipantsWizard(models.TransientModel):
    _name = "federation.import.tournament.participants.wizard"
    _description = "Import Tournament Participants Wizard"

    upload_file = fields.Binary(string="CSV File", required=True)
    upload_filename = fields.Char(string="Filename")
    dry_run = fields.Boolean(string="Dry Run", default=True)
    result_message = fields.Text(string="Result", readonly=True)
    line_count = fields.Integer(string="Total Lines", readonly=True)
    success_count = fields.Integer(string="Success", readonly=True)
    error_count = fields.Integer(string="Errors", readonly=True)

    def action_parse_and_import(self):
        """Parse CSV and import tournament participants."""
        self.ensure_one()

        if not self.upload_file:
            raise ValidationError("Please upload a CSV file.")

        # Decode file
        content = base64.b64decode(self.upload_file)
        content_str = content.decode("utf-8-sig")

        # Parse CSV
        reader = csv.DictReader(io.StringIO(content_str))
        required_columns = ["tournament_name", "team_name"]
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

        Participant = self.env["federation.tournament.participant"]
        Tournament = self.env["federation.tournament"]
        Team = self.env["federation.team"]

        for row_num, row in enumerate(reader, start=2):
            line_count += 1
            tournament_name = row.get("tournament_name", "").strip()
            team_name = row.get("team_name", "").strip()

            if not tournament_name:
                errors.append(f"Row {row_num}: Tournament name is required.")
                error_count += 1
                continue

            if not team_name:
                errors.append(f"Row {row_num}: Team name is required.")
                error_count += 1
                continue

            # Resolve tournament
            tournament = Tournament.search([("name", "=", tournament_name)], limit=1)
            if not tournament:
                errors.append(f"Row {row_num}: Tournament '{tournament_name}' not found.")
                error_count += 1
                continue

            # Resolve team
            team = Team.search([("name", "=", team_name)], limit=1)
            if not team:
                errors.append(f"Row {row_num}: Team '{team_name}' not found.")
                error_count += 1
                continue

            # Check for duplicate
            unavailable_reason = tournament.get_participant_team_unavailability_reason(team)
            if unavailable_reason:
                errors.append(f"Row {row_num}: {unavailable_reason}")
                error_count += 1
                continue

            if not self.dry_run:
                try:
                    Participant.create({
                        "tournament_id": tournament.id,
                        "team_id": team.id,
                    })
                    success_count += 1
                except ValidationError as e:
                    errors.append(f"Row {row_num}: {str(e)}")
                    error_count += 1
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
            "res_model": "federation.import.tournament.participants.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }