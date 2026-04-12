import base64
import csv
import io
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class FederationReportSchedule(models.Model):
    _name = "federation.report.schedule"
    _description = "Federation Report Schedule"
    _order = "next_run_on, name"

    REPORT_TYPE_SELECTION = [
        ("operational", "Operational Summary"),
        ("standing_reconciliation", "Standings Reconciliation"),
        ("finance_reconciliation", "Finance Reconciliation"),
        ("workflow_exceptions", "Workflow Exceptions"),
        ("season_checklist", "Season Checklist"),
        ("compliance_summary", "Compliance Summary"),
    ]
    PERIOD_TYPE_SELECTION = [
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
    ]

    name = fields.Char(required=True)
    report_type = fields.Selection(REPORT_TYPE_SELECTION, required=True, default="operational")
    period_type = fields.Selection(PERIOD_TYPE_SELECTION, required=True, default="weekly")
    season_id = fields.Many2one("federation.season", string="Season")
    active = fields.Boolean(default=True)
    next_run_on = fields.Datetime(required=True, default=fields.Datetime.now)
    last_run_on = fields.Datetime(readonly=True)
    last_period_start = fields.Date(readonly=True)
    last_period_end = fields.Date(readonly=True)
    last_row_count = fields.Integer(readonly=True)
    generated_file = fields.Binary(string="Last Generated File", attachment=True, readonly=True)
    generated_filename = fields.Char(readonly=True)
    notes = fields.Text()

    def _get_reporting_window(self):
        self.ensure_one()
        period_end = fields.Date.context_today(self)
        if self.period_type == "monthly":
            period_start = period_end.replace(day=1)
        else:
            period_start = period_end - timedelta(days=6)
        return period_start, period_end

    def _get_next_run_on(self, reference_dt=None):
        self.ensure_one()
        reference_dt = fields.Datetime.to_datetime(reference_dt or fields.Datetime.now())
        if self.period_type == "monthly":
            return fields.Datetime.to_string(reference_dt + relativedelta(months=1))
        return fields.Datetime.to_string(reference_dt + timedelta(days=7))

    def _get_effective_season(self):
        self.ensure_one()
        return self.season_id or self.env["federation.season"].search([
            ("active", "=", True),
        ], limit=1)

    def _build_operational_rows(self):
        season = self._get_effective_season()
        domain = [("season_id", "=", season.id)] if season else []
        rows = self.env["federation.report.operational"].search(domain, order="tournament_id asc")
        headers = [
            "Season",
            "Tournament",
            "Tournament State",
            "Participants",
            "Confirmed Participants",
            "Participant Confirmation %",
            "Matches",
            "Completed Matches",
            "Match Completion %",
            "Frozen Standings",
            "Standing Coverage",
            "Pending Finance Events",
            "Pending Finance Amount",
            "Open Club Compliance Checks",
            "Readiness Status",
        ]
        data = [
            [
                row.season_id.name if row.season_id else "",
                row.tournament_id.name if row.tournament_id else "",
                row.tournament_state or "",
                row.participant_count,
                row.confirmed_participant_count,
                row.participant_confirmation_rate,
                row.match_count,
                row.completed_match_count,
                row.match_completion_rate,
                row.frozen_standing_count,
                row.standing_line_coverage,
                row.pending_finance_event_count,
                row.pending_finance_amount,
                row.open_club_compliance_count,
                row.readiness_status or "",
            ]
            for row in rows
        ]
        season_code = season.code if season else "all_seasons"
        return headers, data, f"operational_{self.period_type}_{season_code}"

    def _build_standing_reconciliation_rows(self):
        season = self._get_effective_season()
        domain = [("season_id", "=", season.id)] if season else []
        rows = self.env["federation.report.standing.reconciliation"].search(
            domain,
            order="tournament_id asc",
        )
        headers = [
            "Season",
            "Tournament",
            "Tournament State",
            "Confirmed Participants",
            "Covered Participants",
            "Frozen Standings",
            "Missing Participants",
            "Orphaned Participants",
            "Reconciliation Status",
            "Reconciliation Note",
        ]
        data = [
            [
                row.season_id.name if row.season_id else "",
                row.tournament_id.name if row.tournament_id else "",
                row.tournament_state or "",
                row.confirmed_participant_count,
                row.covered_participant_count,
                row.frozen_standing_count,
                row.missing_participant_count,
                row.orphaned_participant_count,
                row.reconciliation_status or "",
                row.reconciliation_note or "",
            ]
            for row in rows
        ]
        season_code = season.code if season else "all_seasons"
        return headers, data, f"standing_reconciliation_{self.period_type}_{season_code}"

    def _build_finance_reconciliation_rows(self):
        rows = self.env["federation.report.finance.reconciliation"].search(
            [("needs_follow_up", "=", True)],
            order="follow_up_status asc, created_on desc",
        )
        headers = [
            "Finance Event",
            "Fee Type",
            "State",
            "Follow-up Status",
            "Counterparty",
            "Source Model",
            "Source Record ID",
            "Amount",
            "External Ref",
            "Invoice Ref",
            "Age (Days)",
            "Needs Follow-up",
        ]
        data = [
            [
                row.finance_event_id.name if row.finance_event_id else "",
                row.fee_type_id.name if row.fee_type_id else "",
                row.state or "",
                row.follow_up_status or "",
                row.counterparty_display or "",
                row.source_model or "",
                row.source_res_id,
                row.amount,
                row.external_ref or "",
                row.invoice_ref or "",
                row.age_days,
                row.needs_follow_up,
            ]
            for row in rows
        ]
        return headers, data, f"finance_reconciliation_{self.period_type}"

    def _build_workflow_exception_rows(self):
        season = self._get_effective_season()
        domain = [(
            "season_id",
            "=",
            season.id,
        )] if season else []
        rows = self.env["federation.report.workflow.exception"].search(
            domain,
            order="age_days desc, raised_on asc",
        )
        headers = [
            "Season",
            "Tournament",
            "Reference",
            "State",
            "Exception Type",
            "Raised On",
            "Age (Days)",
            "Responsible User",
            "Note",
        ]
        data = [
            [
                row.season_id.name if row.season_id else "",
                row.tournament_id.name if row.tournament_id else "",
                row.reference_name or "",
                row.state or "",
                dict(self.env["federation.report.workflow.exception"]._fields["exception_type"].selection).get(
                    row.exception_type,
                    row.exception_type or "",
                ),
                row.raised_on or "",
                row.age_days,
                row.responsible_user_id.name if row.responsible_user_id else "",
                row.exception_note or "",
            ]
            for row in rows
        ]
        season_code = season.code if season else "all_seasons"
        return headers, data, f"workflow_exceptions_{self.period_type}_{season_code}"

    def _build_season_checklist_rows(self):
        season = self._get_effective_season()
        domain = [("season_id", "=", season.id)] if season else []
        rows = self.env["federation.report.season.checklist"].search(domain, order="season_id asc")
        headers = [
            "Season",
            "Season State",
            "Draft Season Registrations",
            "Submitted Season Registrations",
            "Draft Tournament Registrations",
            "Submitted Tournament Registrations",
            "Live Tournaments",
            "Published Tournaments",
            "Unpublished Tournaments",
            "Workflow Exceptions",
            "Checklist Status",
            "Checklist Note",
        ]
        data = [
            [
                row.season_id.name if row.season_id else "",
                row.season_state or "",
                row.draft_season_registration_count,
                row.submitted_season_registration_count,
                row.draft_tournament_registration_count,
                row.submitted_tournament_registration_count,
                row.live_tournament_count,
                row.published_tournament_count,
                row.unpublished_tournament_count,
                row.workflow_exception_count,
                row.checklist_status or "",
                row.checklist_note or "",
            ]
            for row in rows
        ]
        season_code = season.code if season else "all_seasons"
        return headers, data, f"season_checklist_{self.period_type}_{season_code}"

    def _build_compliance_summary_rows(self):
        rows = self.env["federation.report.compliance"].search([], order="target_model asc")
        headers = [
            "Target Model",
            "Compliant",
            "Missing",
            "Pending",
            "Expired",
            "Non Compliant",
        ]
        data = [
            [
                row.target_model or "",
                row.compliant_count,
                row.missing_count,
                row.pending_count,
                row.expired_count,
                row.non_compliant_count,
            ]
            for row in rows
        ]
        return headers, data, f"compliance_summary_{self.period_type}"

    def _build_report_payload(self):
        self.ensure_one()
        builders = {
            "operational": self._build_operational_rows,
            "standing_reconciliation": self._build_standing_reconciliation_rows,
            "finance_reconciliation": self._build_finance_reconciliation_rows,
            "workflow_exceptions": self._build_workflow_exception_rows,
            "season_checklist": self._build_season_checklist_rows,
            "compliance_summary": self._build_compliance_summary_rows,
        }
        headers, rows, slug = builders[self.report_type]()

        period_start, period_end = self._get_reporting_window()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Report", dict(self._fields["report_type"].selection).get(self.report_type, self.report_type)])
        writer.writerow(["Cadence", dict(self._fields["period_type"].selection).get(self.period_type, self.period_type)])
        writer.writerow(["Period Start", period_start])
        writer.writerow(["Period End", period_end])
        writer.writerow([])
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)

        filename = f"{slug}_{period_start}_{period_end}.csv"
        return output.getvalue().encode(), filename, len(rows), period_start, period_end

    def _generate_report(self):
        run_at = fields.Datetime.now()
        for schedule in self:
            payload, filename, row_count, period_start, period_end = schedule._build_report_payload()
            schedule.write({
                "last_run_on": run_at,
                "last_period_start": period_start,
                "last_period_end": period_end,
                "last_row_count": row_count,
                "generated_filename": filename,
                "generated_file": base64.b64encode(payload),
                "next_run_on": schedule._get_next_run_on(run_at),
            })

    def action_generate_now(self):
        self._generate_report()
        return True

    def action_open_report(self):
        self.ensure_one()
        action_xmlid = {
            "operational": "sports_federation_reporting.action_federation_report_operational",
            "standing_reconciliation": "sports_federation_reporting.action_federation_report_standing_reconciliation",
            "finance_reconciliation": "sports_federation_reporting.action_federation_report_finance_reconciliation",
            "workflow_exceptions": "sports_federation_reporting.action_federation_report_workflow_exception",
            "season_checklist": "sports_federation_reporting.action_federation_report_season_checklist",
            "compliance_summary": "sports_federation_reporting.action_federation_report_compliance",
        }[self.report_type]

        action = self.env["ir.actions.act_window"]._for_xml_id(action_xmlid)
        if self.report_type in (
            "operational",
            "standing_reconciliation",
            "workflow_exceptions",
            "season_checklist",
        ) and self.season_id:
            action["domain"] = [("season_id", "=", self.season_id.id)]
        if self.report_type == "finance_reconciliation":
            action["context"] = {"search_default_needs_follow_up": 1}
        return action

    @api.model
    def _cron_generate_scheduled_reports(self):
        schedules = self.search([
            ("active", "=", True),
            ("next_run_on", "!=", False),
            ("next_run_on", "<=", fields.Datetime.now()),
        ], limit=20)
        schedules._generate_report()