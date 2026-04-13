import base64
from datetime import timedelta

from odoo import fields
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
        cls.player = cls.env["federation.player"].create({
            "first_name": "Ops",
            "last_name": "Player",
            "gender": "male",
        })
        cls.disciplinary_case = cls.env["federation.disciplinary.case"].create({
            "name": "Ops Discipline Case",
            "subject_player_id": cls.player.id,
            "summary": "Case used to test finance exception reporting.",
        })
        cls.fine_sanction = cls.env["federation.sanction"].create({
            "name": "Ops Fine",
            "case_id": cls.disciplinary_case.id,
            "sanction_type": "fine",
            "player_id": cls.player.id,
            "amount": 125.0,
            "effective_date": "2026-04-05",
        })
        cls.env["federation.finance.event"].search([
            ("source_model", "=", "federation.sanction"),
            ("source_res_id", "=", cls.fine_sanction.id),
        ]).unlink()
        cls.failed_notification = cls.env["federation.notification.log"].create({
            "name": "Ops Failed Notification",
            "target_model": "federation.match",
            "target_res_id": cls.match.id,
            "notification_type": "email",
            "template_xmlid": "sports_federation_notifications.template_missing",
            "recipient_email": "ops.alerts@example.com",
            "state": "failed",
            "message": "Template lookup failed.",
        })
        stale_dt = fields.Datetime.now() - timedelta(days=4)
        cls.stale_result_match = cls.env["federation.match"].create({
            "tournament_id": cls.tournament.id,
            "home_team_id": cls.team_a.id,
            "away_team_id": cls.team_b.id,
            "state": "done",
            "home_score": 0,
            "away_score": 0,
            "result_state": "verified",
            "result_verified_on": stale_dt,
        })
        cls.stale_override_request = cls.env["federation.override.request"].create({
            "name": "Ops Approved Override",
            "request_type": "standing_adjustment",
            "target_model": "federation.tournament",
            "target_res_id": cls.tournament.id,
            "reason": "Used to test workflow exception reporting.",
            "requested_on": stale_dt,
            "state": "approved",
        })
        cls.team_c = cls.env["federation.team"].create({
            "name": "Ops Team C",
            "club_id": cls.club.id,
            "code": "OPSC",
        })
        cls.season_registration = cls.env["federation.season.registration"].create({
            "season_id": cls.season.id,
            "team_id": cls.team_c.id,
        })
        cls.season_registration.action_submit()
        cls.team_d = cls.env["federation.team"].create({
            "name": "Ops Team D",
            "club_id": cls.club.id,
            "code": "OPSD",
        })
        cls.tournament_registration = cls.env["federation.tournament.registration"].create({
            "tournament_id": cls.tournament.id,
            "team_id": cls.team_d.id,
        })

    def test_operational_report_surfaces_tournament_kpis(self):
        row = self.env["federation.report.operational"].search([
            ("tournament_id", "=", self.tournament.id),
        ], limit=1)

        self.assertTrue(row)
        self.assertEqual(row.participant_count, 2)
        self.assertEqual(row.confirmed_participant_count, 2)
        self.assertEqual(row.completed_match_count, 2)
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
        self.assertEqual(row.queue_owner_display, "Federation Managers")
        self.assertIn(row.sla_status, ("overdue", "escalated", "due_today", "within_sla"))

    def test_notification_exception_report_shows_failed_logs(self):
        row = self.env["federation.report.notification.exception"].search([
            ("notification_log_id", "=", self.failed_notification.id),
        ], limit=1)

        self.assertTrue(row)
        self.assertEqual(row.notification_type, "email")
        self.assertEqual(row.recipient_email, "ops.alerts@example.com")
        self.assertIn("Template lookup failed", row.message)
        self.assertIn(row.sla_status, ("overdue", "escalated", "due_today", "within_sla"))

    def test_finance_exception_report_shows_missing_sanction_event(self):
        row = self.env["federation.report.finance.exception"].search([
            ("sanction_id", "=", self.fine_sanction.id),
        ], limit=1)

        self.assertTrue(row)
        self.assertEqual(row.issue_type, "missing_fine_event")
        self.assertEqual(row.expected_amount, 125.0)
        self.assertEqual(row.player_id, self.player)

    def test_workflow_exception_report_surfaces_stalled_result_and_override(self):
        result_row = self.env["federation.report.workflow.exception"].search([
            ("match_id", "=", self.stale_result_match.id),
        ], limit=1)
        override_row = self.env["federation.report.workflow.exception"].search([
            ("override_request_id", "=", self.stale_override_request.id),
        ], limit=1)

        self.assertTrue(result_row)
        self.assertEqual(result_row.exception_type, "result_approval_stalled")
        self.assertEqual(result_row.tournament_id, self.tournament)
        self.assertGreaterEqual(result_row.age_days, 3)

        self.assertTrue(override_row)
        self.assertEqual(override_row.exception_type, "override_implementation_stalled")
        self.assertGreaterEqual(override_row.age_days, 3)
        self.assertIn(override_row.sla_status, ("overdue", "escalated"))

    def test_compliance_remediation_queue_surfaces_pending_submissions(self):
        submission = self.env["federation.document.submission"].create({
            "name": "Ops Insurance Submission",
            "requirement_id": self.requirement.id,
            "club_id": self.club.id,
        })
        submission.action_submit()

        row = self.env["federation.report.compliance.remediation"].search([
            ("submission_id", "=", submission.id),
        ], limit=1)

        self.assertTrue(row)
        self.assertEqual(row.status, "submitted")
        self.assertEqual(row.target_display, self.club.name)
        self.assertEqual(row.queue_owner_display, "Compliance Review Queue")
        self.assertIn(row.sla_status, ("within_sla", "due_today", "overdue", "escalated"))

    def test_compliance_remediation_queue_surfaces_expired_approved_submissions(self):
        submission = self.env["federation.document.submission"].create({
            "name": "Ops Expired Submission",
            "requirement_id": self.requirement.id,
            "club_id": self.club.id,
            "issue_date": fields.Date.today() - timedelta(days=365),
            "expiry_date": fields.Date.today() - timedelta(days=1),
        })
        submission.action_submit()
        submission.action_approve()

        row = self.env["federation.report.compliance.remediation"].search([
            ("submission_id", "=", submission.id),
        ], limit=1)

        self.assertTrue(row)
        self.assertEqual(row.status, "expired")
        self.assertIn("renewal", row.remediation_note.lower())

    def test_season_checklist_flags_open_work_for_season(self):
        row = self.env["federation.report.season.checklist"].search([
            ("season_id", "=", self.season.id),
        ], limit=1)

        self.assertTrue(row)
        self.assertEqual(row.submitted_season_registration_count, 1)
        self.assertEqual(row.draft_tournament_registration_count, 1)
        self.assertEqual(row.unpublished_tournament_count, 1)
        self.assertGreaterEqual(row.workflow_exception_count, 1)
        self.assertEqual(row.checklist_status, "blocked")

    def test_workflow_exception_schedule_generates_attachment(self):
        schedule = self.env["federation.report.schedule"].create({
            "name": "Workflow Exceptions",
            "report_type": "workflow_exceptions",
            "period_type": "weekly",
            "season_id": self.season.id,
        })

        schedule.action_generate_now()

        self.assertTrue(schedule.generated_file)
        csv_payload = base64.b64decode(schedule.generated_file).decode()
        self.assertIn("Workflow Exceptions", csv_payload)
        self.assertIn(self.stale_result_match.name, csv_payload)

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

    def test_snapshot_capture_and_board_pack_generation(self):
        snapshots = self.env["federation.report.snapshot"].capture_snapshot()

        self.assertTrue(snapshots)
        self.assertEqual(len(snapshots), 5)

        board_pack = self.env["federation.report.schedule"].create({
            "name": "Board Pack",
            "report_type": "board_pack",
            "period_type": "weekly",
        })
        board_pack.action_generate_now()

        self.assertTrue(board_pack.generated_file)
        board_payload = base64.b64decode(board_pack.generated_file).decode()
        self.assertIn("Board Pack", board_payload)
        self.assertIn("Override Backlog", board_payload)

    def test_audit_pack_includes_operational_queues(self):
        schedule = self.env["federation.report.schedule"].create({
            "name": "Audit Pack",
            "report_type": "audit_pack",
            "period_type": "weekly",
        })

        schedule.action_generate_now()

        self.assertTrue(schedule.generated_file)
        audit_payload = base64.b64decode(schedule.generated_file).decode()
        self.assertIn("Audit Pack", audit_payload)
        self.assertIn("Workflow Exceptions", audit_payload)
        self.assertIn("Finance Follow-up", audit_payload)