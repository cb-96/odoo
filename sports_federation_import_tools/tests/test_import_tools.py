import base64

from odoo.exceptions import AccessError
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase


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
            "code": "TEAM001",
            "club_id": cls.club.id,
        })

    def _create_csv_file(self, content):
        """Helper to create a CSV file binary."""
        return base64.b64encode(content.encode("utf-8"))

    def _approve_wizard_import(self, wizard):
        wizard.dry_run = True
        wizard.action_parse_and_import()
        wizard.action_request_approval()
        wizard.action_approve_import()
        wizard.dry_run = False
        return wizard

    def _create_integration_partner(self, contract):
        partner = self.env["federation.integration.partner"].create({
            "name": f"Partner {contract.code}",
            "code": f"PARTNER_{contract.code.upper()}",
        })
        subscription = self.env["federation.integration.partner.contract"].create({
            "partner_id": partner.id,
            "contract_id": contract.id,
        })
        return partner, subscription

    def test_import_clubs_dry_run_exposes_mapping_guide(self):
        """Clubs dry-run should validate rows without creating records and show guidance."""
        csv_content = "name;code;email;phone;city\nNew Club;NC001;new@example.com;123456;City1"
        wizard = self.env["federation.import.clubs.wizard"].create({
            "upload_file": self._create_csv_file(csv_content),
            "dry_run": True,
        })

        self.assertIn("Recommended columns", wizard.mapping_guide)

        wizard.action_parse_and_import()

        self.assertEqual(wizard.line_count, 1)
        self.assertEqual(wizard.success_count, 1)
        self.assertEqual(wizard.error_count, 0)
        self.assertTrue(wizard.template_id)
        self.assertFalse(self.env["federation.club"].search([("name", "=", "New Club")]))

    def test_import_governance_requires_approval_for_live_run(self):
        csv_content = "name;code;email;phone;city\nGoverned Club;GC001;gov@example.com;123456;City1"
        wizard = self.env["federation.import.clubs.wizard"].create({
            "upload_file": self._create_csv_file(csv_content),
            "dry_run": True,
        })

        wizard.action_parse_and_import()
        wizard.action_request_approval()

        self.assertTrue(wizard.governance_job_id)
        self.assertEqual(wizard.governance_job_id.state, "awaiting_approval")
        self.assertIn("Preview totals", wizard.governance_job_id.verification_summary)

        wizard.dry_run = False
        with self.assertRaises(ValidationError):
            wizard.action_parse_and_import()

        wizard.action_approve_import()
        self.assertEqual(wizard.governance_job_id.state, "approved")

        wizard.action_parse_and_import()

        self.assertEqual(wizard.governance_job_id.state, "completed")
        self.assertEqual(wizard.governance_job_id.pre_import_record_count + 1, wizard.governance_job_id.post_import_record_count)
        self.assertIn("Net new target records: 1", wizard.governance_job_id.verification_summary)
        self.assertTrue(self.env["federation.club"].search([("code", "=", "GC001")], limit=1))

    def test_import_governance_invalidates_approval_when_file_changes(self):
        initial_csv = "name;code\nInitial Club;IC001"
        wizard = self.env["federation.import.clubs.wizard"].create({
            "upload_file": self._create_csv_file(initial_csv),
            "dry_run": True,
        })

        wizard.action_parse_and_import()
        wizard.action_request_approval()
        wizard.action_approve_import()

        wizard.write({
            "upload_file": self._create_csv_file("name;code\nChanged Club;CC001"),
            "dry_run": False,
        })

        with self.assertRaises(ValidationError):
            wizard.action_parse_and_import()

    def test_partner_authentication_requires_subscription(self):
        contract = self.env.ref(
            "sports_federation_import_tools.federation_integration_contract_finance_event"
        )
        partner, subscription = self._create_integration_partner(contract)

        auth_partner, auth_subscription = self.env[
            "federation.integration.partner"
        ].authenticate_partner(
            partner.code,
            partner.auth_token,
            contract_code=contract.code,
        )

        self.assertEqual(auth_partner, partner)
        self.assertEqual(auth_subscription, subscription)
        self.assertTrue(subscription.last_used_on)

        with self.assertRaises(AccessError):
            self.env["federation.integration.partner"].authenticate_partner(
                partner.code,
                "wrong-token",
                contract_code=contract.code,
            )

    def test_inbound_delivery_stages_and_reuses_duplicate_payloads(self):
        contract = self.env.ref(
            "sports_federation_import_tools.federation_integration_contract_clubs_csv"
        )
        partner, _subscription = self._create_integration_partner(contract)
        payload = self._create_csv_file("name;code\nStaged Club;SC001").decode("utf-8")

        delivery = self.env["federation.integration.delivery"].stage_partner_delivery(
            partner=partner,
            contract=contract,
            filename="clubs.csv",
            payload_base64=payload,
            source_reference="batch-001",
        )
        duplicate = self.env["federation.integration.delivery"].stage_partner_delivery(
            partner=partner,
            contract=contract,
            filename="clubs.csv",
            payload_base64=payload,
            source_reference="batch-001",
        )

        self.assertEqual(delivery, duplicate)
        self.assertEqual(delivery.state, "staged")
        self.assertTrue(delivery.attachment_id)
        self.assertEqual(delivery.import_template_id, contract.import_template_id)

    def test_inbound_delivery_links_to_governed_import_flow(self):
        contract = self.env.ref(
            "sports_federation_import_tools.federation_integration_contract_clubs_csv"
        )
        partner, _subscription = self._create_integration_partner(contract)
        payload = self._create_csv_file("name;code\nDelivery Club;DC001").decode("utf-8")
        delivery = self.env["federation.integration.delivery"].stage_partner_delivery(
            partner=partner,
            contract=contract,
            filename="delivery-clubs.csv",
            payload_base64=payload,
        )

        action = delivery.action_open_import_wizard()
        wizard = self.env[action["res_model"]].browse(action["res_id"])

        self.assertEqual(wizard.integration_delivery_id, delivery)
        self.assertEqual(wizard.template_id, contract.import_template_id)

        wizard.action_parse_and_import()
        delivery.invalidate_recordset()
        self.assertEqual(delivery.state, "previewed")

        wizard.action_request_approval()
        delivery.invalidate_recordset()
        self.assertEqual(delivery.state, "awaiting_approval")
        self.assertEqual(delivery.governance_job_id, wizard.governance_job_id)

        wizard.action_approve_import()
        delivery.invalidate_recordset()
        self.assertEqual(delivery.state, "approved")

        wizard.dry_run = False
        wizard.action_parse_and_import()
        delivery.invalidate_recordset()

        self.assertEqual(delivery.state, "processed")
        self.assertEqual(delivery.governance_job_id.state, "completed")
        self.assertEqual(delivery.success_count, 1)
        self.assertTrue(self.env["federation.club"].search([("code", "=", "DC001")], limit=1))

    def test_import_teams_resolves_club_by_code(self):
        """Teams import should resolve parent clubs via club codes and create the record."""
        csv_content = (
            "club_code,team_name,code,category,gender,email,phone\n"
            "TC001,Reserve Team,TEAM002,youth,mixed,reserve@example.com,555"
        )
        wizard = self._approve_wizard_import(self.env["federation.import.teams.wizard"].create({
            "upload_file": self._create_csv_file(csv_content),
            "dry_run": False,
        }))

        wizard.action_parse_and_import()

        self.assertEqual(wizard.line_count, 1)
        self.assertEqual(wizard.success_count, 1)
        self.assertEqual(wizard.error_count, 0)

        team = self.env["federation.team"].search([("code", "=", "TEAM002")], limit=1)
        self.assertTrue(team)
        self.assertEqual(team.club_id, self.club)
        self.assertEqual(team.category, "youth")
        self.assertEqual(team.gender, "mixed")

    def test_import_players_splits_legacy_name_and_sets_club(self):
        """Players import should translate legacy full-name CSVs into first and last names."""
        csv_content = "name,birth_date,club_code,gender,state\nAlice Example,2005-04-06,TC001,female,active"
        wizard = self._approve_wizard_import(self.env["federation.import.players.wizard"].create({
            "upload_file": self._create_csv_file(csv_content),
            "dry_run": False,
        }))

        wizard.action_parse_and_import()

        self.assertEqual(wizard.line_count, 1)
        self.assertEqual(wizard.success_count, 1)
        self.assertEqual(wizard.error_count, 0)

        player = self.env["federation.player"].search([
            ("first_name", "=", "Alice"),
            ("last_name", "=", "Example"),
        ], limit=1)
        self.assertTrue(player)
        self.assertEqual(player.club_id, self.club)
        self.assertEqual(player.gender, "female")

    def test_import_seasons_reports_format_errors_by_category(self):
        """Season import should create valid rows and classify invalid date rows."""
        csv_content = (
            "name,code,date_start,date_end,state\n"
            "Season 2026,S2026,2026-01-01,2026-12-31,open\n"
            "Season 2027,S2027,2026/01/01,2026-12-31,open"
        )
        wizard = self.env["federation.import.seasons.wizard"].create({
            "upload_file": self._create_csv_file(csv_content),
            "dry_run": False,
        })

        self._approve_wizard_import(wizard)

        wizard.action_parse_and_import()

        self.assertEqual(wizard.line_count, 2)
        self.assertEqual(wizard.success_count, 1)
        self.assertEqual(wizard.error_count, 1)
        self.assertIn("format_error", wizard.result_message)
        self.assertTrue(self.env["federation.season"].search([("code", "=", "S2026")], limit=1))

    def test_import_seasons_supports_planning_targets(self):
        csv_content = (
            "name,code,date_start,date_end,state,target_club_count,target_team_count,target_tournament_count,target_participant_count\n"
            "Planning Season,SPLAN,2026-01-01,2026-12-31,draft,8,18,4,32"
        )
        wizard = self.env["federation.import.seasons.wizard"].create({
            "upload_file": self._create_csv_file(csv_content),
            "dry_run": False,
        })

        self._approve_wizard_import(wizard)
        wizard.action_parse_and_import()

        season = self.env["federation.season"].search([("code", "=", "SPLAN")], limit=1)
        self.assertTrue(season)
        self.assertEqual(season.target_club_count, 8)
        self.assertEqual(season.target_team_count, 18)
        self.assertEqual(season.target_tournament_count, 4)
        self.assertEqual(season.target_participant_count, 32)

    def test_import_tournament_participants_duplicate_skip(self):
        """Tournament participant import should block duplicate rows using the shared backend reason."""
        self.env["federation.tournament.participant"].create({
            "tournament_id": self.tournament.id,
            "team_id": self.team.id,
        })

        csv_content = f"tournament_code,team_code\n{self.tournament.code},{self.team.code}"
        wizard = self._approve_wizard_import(self.env["federation.import.tournament.participants.wizard"].create({
            "upload_file": self._create_csv_file(csv_content),
            "dry_run": False,
        }))

        wizard.action_parse_and_import()

        self.assertEqual(wizard.line_count, 1)
        self.assertEqual(wizard.success_count, 0)
        self.assertEqual(wizard.error_count, 1)
        self.assertIn("A participant record already exists for this team.", wizard.result_message)
        self.assertIn("duplicate_entry", wizard.result_message)

    def test_import_tournament_participants_accepts_codes_and_seed(self):
        """Tournament participant import should resolve references by code and persist seed."""
        tournament = self.env["federation.tournament"].create({
            "name": "Spring Invitational",
            "code": "SPRING2026",
            "date_start": "2026-03-01",
            "date_end": "2026-03-02",
        })
        team = self.env["federation.team"].create({
            "name": "Seeded Team",
            "code": "TEAM003",
            "club_id": self.club.id,
        })

        csv_content = f"tournament_code,team_code,seed\n{tournament.code},{team.code},4"
        wizard = self._approve_wizard_import(self.env["federation.import.tournament.participants.wizard"].create({
            "upload_file": self._create_csv_file(csv_content),
            "dry_run": False,
        }))

        wizard.action_parse_and_import()

        self.assertEqual(wizard.line_count, 1)
        self.assertEqual(wizard.success_count, 1)
        self.assertEqual(wizard.error_count, 0)

        participant = self.env["federation.tournament.participant"].search([
            ("tournament_id", "=", tournament.id),
            ("team_id", "=", team.id),
        ], limit=1)
        self.assertTrue(participant)
        self.assertEqual(participant.seed, 4)