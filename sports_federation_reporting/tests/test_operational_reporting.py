import base64

from odoo.tests.common import TransactionCase


class TestOperationalReporting(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.club = cls.env["federation.club"].create({
            "name": "Ops Club",
            "code": "OPSCL",
            "email": "ops.club@example.com",
        })
        cls.season = cls.env["federation.season"].create({
            "name": "Ops Season",
            "code": "OPS2026",
            "date_start": "2026-01-01",
            "date_end": "2026-12-31",
            "active": True,
        })
        cls.team_a = cls.env["federation.team"].create({
            "name": "Ops Team A",
            "club_id": cls.club.id,
            "code": "OPSA",
        })
        cls.team_b = cls.env["federation.team"].create({
            "name": "Ops Team B",
            "club_id": cls.club.id,
            "code": "OPSB",
        })
        cls.tournament = cls.env["federation.tournament"].create({
            "name": "Ops Tournament",
            "code": "OPST",
            "season_id": cls.season.id,
            "date_start": "2026-04-01",
            "state": "in_progress",
        })
        cls.participant_a = cls.env["federation.tournament.participant"].create({
            "tournament_id": cls.tournament.id,
            "team_id": cls.team_a.id,
            "state": "confirmed",
        })
        cls.participant_b = cls.env["federation.tournament.participant"].create({
            "tournament_id": cls.tournament.id,
            "team_id": cls.team_b.id,
            "state": "confirmed",
        })
        cls.match = cls.env["federation.match"].create({
            "tournament_id": cls.tournament.id,
            "home_team_id": cls.team_a.id,
            "away_team_id": cls.team_b.id,
            "state": "done",
            "home_score": 1,
            "away_score": 0,
        })
        cls.rule_set = cls.env["federation.rule.set"].create({
            "name": "Ops Rules",
            "code": "OPSR",
            "points_win": 3,
            "points_draw": 1,
            "points_loss": 0,
        })
        cls.standing = cls.env["federation.standing"].create({
            "name": "Ops Standing",
            "tournament_id": cls.tournament.id,
            "rule_set_id": cls.rule_set.id,
        })
        cls.env["federation.standing.line"].create({
            "standing_id": cls.standing.id,
            "participant_id": cls.participant_a.id,
            "rank": 1,
            "played": 1,
            "won": 1,
            "lost": 0,
            "points": 3,
        })
        cls.requirement = cls.env["federation.document.requirement"].create({
            "name": "Ops Insurance",
            "code": "OPSINS",
            "target_model": "federation.club",
            "required_for_all": True,
        })
        cls.env["federation.compliance.check"].create({
            "name": "Ops Club Insurance",
            "target_model": "federation.club",
            "club_id": cls.club.id,
            "status": "missing",
            "requirement_id": cls.requirement.id,
        })
        cls.fee_type = cls.env["federation.fee.type"].create({
            "name": "Ops Venue Fee",
            "code": "OPSFEE",
            "category": "other",
            "default_amount": 55.0,
        })
        cls.finance_event = cls.env["federation.finance.event"].create({
            "name": "Ops Match Charge",
            "fee_type_id": cls.fee_type.id,
            "event_type": "charge",
            "amount": 55.0,
            "source_model": "federation.match",
            "source_res_id": cls.match.id,
            "club_id": cls.club.id,
        })

    def test_operational_report_surfaces_tournament_kpis(self):
        row = self.env["federation.report.operational"].search([
            ("tournament_id", "=", self.tournament.id),
        ], limit=1)

        self.assertTrue(row)
        self.assertEqual(row.participant_count, 2)
        self.assertEqual(row.confirmed_participant_count, 2)
        self.assertEqual(row.completed_match_count, 1)
        self.assertEqual(row.standing_line_coverage, 1)
        self.assertEqual(row.pending_finance_event_count, 1)
        self.assertEqual(row.open_club_compliance_count, 1)
        self.assertEqual(row.readiness_status, "blocked")

    def test_standing_reconciliation_flags_missing_participants(self):
        row = self.env["federation.report.standing.reconciliation"].search([
            ("tournament_id", "=", self.tournament.id),
        ], limit=1)

        self.assertTrue(row)
        self.assertEqual(row.confirmed_participant_count, 2)
        self.assertEqual(row.covered_participant_count, 1)
        self.assertEqual(row.missing_participant_count, 1)
        self.assertEqual(row.reconciliation_status, "attention")

    def test_finance_reconciliation_flags_open_items(self):
        row = self.env["federation.report.finance.reconciliation"].search([
            ("finance_event_id", "=", self.finance_event.id),
        ], limit=1)

        self.assertTrue(row)
        self.assertEqual(row.follow_up_status, "draft")
        self.assertTrue(row.needs_follow_up)
        self.assertEqual(row.counterparty_display, self.club.name)

    def test_report_schedule_generates_attachment(self):
        schedule = self.env["federation.report.schedule"].create({
            "name": "Weekly Operations",
            "report_type": "operational",
            "period_type": "weekly",
            "season_id": self.season.id,
        })

        schedule.action_generate_now()

        self.assertTrue(schedule.generated_file)
        self.assertTrue(schedule.generated_filename)
        self.assertTrue(schedule.last_run_on)
        self.assertTrue(schedule.next_run_on)
        csv_payload = base64.b64decode(schedule.generated_file).decode()
        self.assertIn("Operational Summary", csv_payload)
        self.assertIn(self.tournament.name, csv_payload)