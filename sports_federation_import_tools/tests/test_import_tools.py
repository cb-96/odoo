import base64

from odoo.tests import TransactionCase
from odoo.exceptions import ValidationError


class TestImportTools(TransactionCase):
    """Test cases for import tools wizards."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create test club
        cls.club = cls.env["federation.club"].create({
            "name": "Test Club",
            "code": "TC001",
        })
        # Create test tournament
        cls.tournament = cls.env["federation.tournament"].create({
            "name": "Test Tournament",
            "code": "TT2024",
            "date_start": "2024-01-01",
            "date_end": "2024-01-31",
        })
        # Create test team
        cls.team = cls.env["federation.team"].create({
            "name": "Test Team",
            "club_id": cls.club.id,
        })

    def _create_csv_file(self, content):
        """Helper to create a CSV file binary."""
        return base64.b64encode(content.encode("utf-8"))

    def test_import_clubs_dry_run(self):
        """Test clubs import in dry run mode."""
        csv_content = "name,email,phone,city\nNew Club,new@example.com,123456,City1"
        wizard = self.env["federation.import.clubs.wizard"].create({
            "upload_file": self._create_csv_file(csv_content),
            "dry_run": True,
        })
        wizard.action_parse_and_import()
        self.assertEqual(wizard.line_count, 1)
        self.assertEqual(wizard.success_count, 1)
        self.assertEqual(wizard.error_count, 0)
        # Verify no club was created
        self.assertFalse(self.env["federation.club"].search([("name", "=", "New Club")]))

    def test_import_clubs_real(self):
        """Test clubs import in real mode."""
        csv_content = "name,email,phone,city\nReal Club,real@example.com,123456,City1"
        wizard = self.env["federation.import.clubs.wizard"].create({
            "upload_file": self._create_csv_file(csv_content),
            "dry_run": False,
        })
        wizard.action_parse_and_import()
        self.assertEqual(wizard.line_count, 1)
        self.assertEqual(wizard.success_count, 1)
        self.assertEqual(wizard.error_count, 0)
        # Verify club was created
        self.assertTrue(self.env["federation.club"].search([("name", "=", "Real Club")]))

    def test_import_teams_missing_club(self):
        """Test teams import with missing club."""
        csv_content = "club_name,team_name\nMissing Club,New Team"
        wizard = self.env["federation.import.teams.wizard"].create({
            "upload_file": self._create_csv_file(csv_content),
            "dry_run": False,
        })
        wizard.action_parse_and_import()
        self.assertEqual(wizard.line_count, 1)
        self.assertEqual(wizard.success_count, 0)
        self.assertEqual(wizard.error_count, 1)
        self.assertIn("not found", wizard.result_message)

    def test_import_players_invalid_date(self):
        """Test players import with invalid date."""
        csv_content = "name,birth_date\nPlayer1,invalid-date"
        wizard = self.env["federation.import.players.wizard"].create({
            "upload_file": self._create_csv_file(csv_content),
            "dry_run": False,
        })
        wizard.action_parse_and_import()
        self.assertEqual(wizard.line_count, 1)
        self.assertEqual(wizard.success_count, 0)
        self.assertEqual(wizard.error_count, 1)
        self.assertIn("Invalid birth_date", wizard.result_message)

    def test_import_tournament_participants_duplicate_skip(self):
        """Test tournament participants import skips duplicates."""
        # Create first participant
        self.env["federation.tournament.participant"].create({
            "tournament_id": self.tournament.id,
            "team_id": self.team.id,
        })
        # Try to import same participant
        csv_content = f"tournament_name,team_name\n{self.tournament.name},{self.team.name}"
        wizard = self.env["federation.import.tournament.participants.wizard"].create({
            "upload_file": self._create_csv_file(csv_content),
            "dry_run": False,
        })
        wizard.action_parse_and_import()
        self.assertEqual(wizard.line_count, 1)
        self.assertEqual(wizard.success_count, 0)
        self.assertEqual(wizard.error_count, 1)
        self.assertIn("A participant record already exists for this team.", wizard.result_message)

    def test_import_tournament_participants_reports_ineligible_reason(self):
        """Test tournament participant import shows the same eligibility reason as backend flows."""
        tournament = self.env["federation.tournament"].create({
            "name": "Senior Men Tournament",
            "code": "SMT2024",
            "date_start": "2024-02-01",
            "category": "senior",
            "gender": "male",
        })
        ineligible_team = self.env["federation.team"].create({
            "name": "Ineligible Team",
            "club_id": self.club.id,
            "code": "IT001",
            "category": "senior",
            "gender": "female",
        })

        csv_content = (
            "tournament_name,team_name\n"
            f"{tournament.name},{ineligible_team.name}"
        )
        wizard = self.env["federation.import.tournament.participants.wizard"].create({
            "upload_file": self._create_csv_file(csv_content),
            "dry_run": False,
        })
        wizard.action_parse_and_import()

        self.assertEqual(wizard.line_count, 1)
        self.assertEqual(wizard.success_count, 0)
        self.assertEqual(wizard.error_count, 1)
        self.assertIn("Ineligible Team", wizard.result_message)
        self.assertIn("is not eligible for tournament", wizard.result_message)