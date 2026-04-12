from odoo import fields, models, tools


class FederationReportOperational(models.Model):
    _name = "federation.report.operational"
    _description = "Federation Operational Report"
    _auto = False
    _order = "season_id, tournament_id"

    STATUS_SELECTION = [
        ("healthy", "Healthy"),
        ("attention", "Attention"),
        ("blocked", "Blocked"),
    ]

    TOURNAMENT_STATE_SELECTION = [
        ("draft", "Draft"),
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("closed", "Closed"),
        ("cancelled", "Cancelled"),
    ]

    season_id = fields.Many2one("federation.season", string="Season", readonly=True)
    tournament_id = fields.Many2one("federation.tournament", string="Tournament", readonly=True)
    tournament_state = fields.Selection(TOURNAMENT_STATE_SELECTION, string="Tournament State", readonly=True)
    date_start = fields.Date(string="Start Date", readonly=True)
    date_end = fields.Date(string="End Date", readonly=True)
    participant_count = fields.Integer(string="Participants", readonly=True)
    confirmed_participant_count = fields.Integer(string="Confirmed Participants", readonly=True)
    participant_confirmation_rate = fields.Float(string="Participant Confirmation %", readonly=True, digits=(16, 2))
    match_count = fields.Integer(string="Matches", readonly=True)
    completed_match_count = fields.Integer(string="Completed Matches", readonly=True)
    match_completion_rate = fields.Float(string="Match Completion %", readonly=True, digits=(16, 2))
    frozen_standing_count = fields.Integer(string="Frozen Standings", readonly=True)
    standing_line_coverage = fields.Integer(string="Standing Coverage", readonly=True)
    pending_finance_event_count = fields.Integer(string="Pending Finance Events", readonly=True)
    pending_finance_amount = fields.Float(string="Pending Finance Amount", readonly=True)
    open_club_compliance_count = fields.Integer(string="Open Club Compliance Checks", readonly=True)
    readiness_status = fields.Selection(STATUS_SELECTION, string="Readiness Status", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE VIEW federation_report_operational AS (
                WITH participant_stats AS (
                    SELECT
                        p.tournament_id,
                        COUNT(*) AS participant_count,
                        COUNT(*) FILTER (WHERE p.state = 'confirmed') AS confirmed_participant_count
                    FROM federation_tournament_participant p
                    GROUP BY p.tournament_id
                ),
                match_stats AS (
                    SELECT
                        m.tournament_id,
                        COUNT(*) AS match_count,
                        COUNT(*) FILTER (WHERE m.state = 'done') AS completed_match_count
                    FROM federation_match m
                    GROUP BY m.tournament_id
                ),
                standing_stats AS (
                    SELECT
                        s.tournament_id,
                        COUNT(*) FILTER (WHERE s.state = 'frozen') AS frozen_standing_count,
                        COUNT(DISTINCT sl.participant_id) AS standing_line_coverage
                    FROM federation_standing s
                    LEFT JOIN federation_standing_line sl ON sl.standing_id = s.id
                    GROUP BY s.tournament_id
                ),
                finance_links AS (
                    SELECT fe.id, fe.state, fe.amount, m.tournament_id
                    FROM federation_finance_event fe
                    JOIN federation_match m
                      ON fe.source_model = 'federation.match'
                     AND fe.source_res_id = m.id

                    UNION ALL

                    SELECT fe.id, fe.state, fe.amount, m.tournament_id
                    FROM federation_finance_event fe
                    JOIN federation_match_referee mr
                      ON fe.source_model = 'federation.match.referee'
                     AND fe.source_res_id = mr.id
                    JOIN federation_match m ON m.id = mr.match_id
                ),
                finance_stats AS (
                    SELECT
                        fl.tournament_id,
                        COUNT(DISTINCT fl.id) FILTER (WHERE fl.state IN ('draft', 'confirmed')) AS pending_finance_event_count,
                        COALESCE(SUM(fl.amount) FILTER (WHERE fl.state IN ('draft', 'confirmed')), 0) AS pending_finance_amount
                    FROM finance_links fl
                    GROUP BY fl.tournament_id
                ),
                club_compliance_stats AS (
                    SELECT
                        p.tournament_id,
                        COUNT(DISTINCT cc.id) AS open_club_compliance_count
                    FROM federation_tournament_participant p
                    JOIN federation_compliance_check cc
                      ON cc.club_id = p.club_id
                     AND cc.status <> 'compliant'
                    GROUP BY p.tournament_id
                )
                SELECT
                    row_number() OVER (ORDER BY s.id, t.id) AS id,
                    s.id AS season_id,
                    t.id AS tournament_id,
                    t.state AS tournament_state,
                    t.date_start,
                    t.date_end,
                    COALESCE(ps.participant_count, 0) AS participant_count,
                    COALESCE(ps.confirmed_participant_count, 0) AS confirmed_participant_count,
                    ROUND(
                        CASE
                            WHEN COALESCE(ps.participant_count, 0) = 0 THEN 0
                            ELSE (COALESCE(ps.confirmed_participant_count, 0)::numeric / ps.participant_count::numeric) * 100
                        END,
                        2
                    ) AS participant_confirmation_rate,
                    COALESCE(ms.match_count, 0) AS match_count,
                    COALESCE(ms.completed_match_count, 0) AS completed_match_count,
                    ROUND(
                        CASE
                            WHEN COALESCE(ms.match_count, 0) = 0 THEN 0
                            ELSE (COALESCE(ms.completed_match_count, 0)::numeric / ms.match_count::numeric) * 100
                        END,
                        2
                    ) AS match_completion_rate,
                    COALESCE(ss.frozen_standing_count, 0) AS frozen_standing_count,
                    COALESCE(ss.standing_line_coverage, 0) AS standing_line_coverage,
                    COALESCE(fs.pending_finance_event_count, 0) AS pending_finance_event_count,
                    COALESCE(fs.pending_finance_amount, 0) AS pending_finance_amount,
                    COALESCE(ccs.open_club_compliance_count, 0) AS open_club_compliance_count,
                    CASE
                        WHEN COALESCE(ccs.open_club_compliance_count, 0) > 0 THEN 'blocked'
                        WHEN COALESCE(ps.participant_count, 0) > COALESCE(ps.confirmed_participant_count, 0)
                          OR (
                              COALESCE(ms.match_count, 0) > 0
                              AND COALESCE(ms.completed_match_count, 0) < COALESCE(ms.match_count, 0)
                          )
                          OR COALESCE(fs.pending_finance_event_count, 0) > 0
                        THEN 'attention'
                        ELSE 'healthy'
                    END AS readiness_status
                FROM federation_tournament t
                LEFT JOIN federation_season s ON s.id = t.season_id
                LEFT JOIN participant_stats ps ON ps.tournament_id = t.id
                LEFT JOIN match_stats ms ON ms.tournament_id = t.id
                LEFT JOIN standing_stats ss ON ss.tournament_id = t.id
                LEFT JOIN finance_stats fs ON fs.tournament_id = t.id
                LEFT JOIN club_compliance_stats ccs ON ccs.tournament_id = t.id
            )
            """
        )


class FederationReportStandingReconciliation(models.Model):
    _name = "federation.report.standing.reconciliation"
    _description = "Federation Standing Reconciliation Report"
    _auto = False
    _order = "season_id, tournament_id"

    STATUS_SELECTION = FederationReportOperational.STATUS_SELECTION
    TOURNAMENT_STATE_SELECTION = FederationReportOperational.TOURNAMENT_STATE_SELECTION

    season_id = fields.Many2one("federation.season", string="Season", readonly=True)
    tournament_id = fields.Many2one("federation.tournament", string="Tournament", readonly=True)
    tournament_state = fields.Selection(TOURNAMENT_STATE_SELECTION, string="Tournament State", readonly=True)
    confirmed_participant_count = fields.Integer(string="Confirmed Participants", readonly=True)
    covered_participant_count = fields.Integer(string="Covered Participants", readonly=True)
    frozen_standing_count = fields.Integer(string="Frozen Standings", readonly=True)
    missing_participant_count = fields.Integer(string="Missing Participants", readonly=True)
    orphaned_participant_count = fields.Integer(string="Orphaned Participants", readonly=True)
    reconciliation_status = fields.Selection(STATUS_SELECTION, string="Reconciliation Status", readonly=True)
    reconciliation_note = fields.Text(string="Reconciliation Note", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE VIEW federation_report_standing_reconciliation AS (
                WITH participant_stats AS (
                    SELECT
                        p.tournament_id,
                        COUNT(*) FILTER (WHERE p.state = 'confirmed') AS confirmed_participant_count
                    FROM federation_tournament_participant p
                    GROUP BY p.tournament_id
                ),
                coverage_stats AS (
                    SELECT
                        s.tournament_id,
                        COUNT(DISTINCT sl.participant_id) AS covered_participant_count,
                        COUNT(DISTINCT s.id) FILTER (WHERE s.state = 'frozen') AS frozen_standing_count
                    FROM federation_standing s
                    LEFT JOIN federation_standing_line sl ON sl.standing_id = s.id
                    GROUP BY s.tournament_id
                )
                SELECT
                    row_number() OVER (ORDER BY se.id, t.id) AS id,
                    se.id AS season_id,
                    t.id AS tournament_id,
                    t.state AS tournament_state,
                    COALESCE(ps.confirmed_participant_count, 0) AS confirmed_participant_count,
                    COALESCE(cs.covered_participant_count, 0) AS covered_participant_count,
                    COALESCE(cs.frozen_standing_count, 0) AS frozen_standing_count,
                    GREATEST(COALESCE(ps.confirmed_participant_count, 0) - COALESCE(cs.covered_participant_count, 0), 0) AS missing_participant_count,
                    GREATEST(COALESCE(cs.covered_participant_count, 0) - COALESCE(ps.confirmed_participant_count, 0), 0) AS orphaned_participant_count,
                    CASE
                        WHEN COALESCE(ps.confirmed_participant_count, 0) > 0 AND COALESCE(cs.covered_participant_count, 0) = 0 THEN 'blocked'
                        WHEN COALESCE(ps.confirmed_participant_count, 0) <> COALESCE(cs.covered_participant_count, 0)
                          OR (
                              t.state IN ('in_progress', 'closed')
                              AND COALESCE(cs.frozen_standing_count, 0) = 0
                              AND COALESCE(ps.confirmed_participant_count, 0) > 0
                          )
                        THEN 'attention'
                        ELSE 'healthy'
                    END AS reconciliation_status,
                    CASE
                        WHEN COALESCE(ps.confirmed_participant_count, 0) > 0 AND COALESCE(cs.covered_participant_count, 0) = 0 THEN 'No standing lines currently cover confirmed participants.'
                        WHEN COALESCE(ps.confirmed_participant_count, 0) <> COALESCE(cs.covered_participant_count, 0) THEN 'Confirmed participant count does not match standing coverage.'
                        WHEN t.state IN ('in_progress', 'closed')
                          AND COALESCE(cs.frozen_standing_count, 0) = 0
                          AND COALESCE(ps.confirmed_participant_count, 0) > 0 THEN 'Tournament has confirmed participants but no frozen standings snapshot.'
                        ELSE 'Standings coverage matches confirmed tournament participants.'
                    END AS reconciliation_note
                FROM federation_tournament t
                LEFT JOIN federation_season se ON se.id = t.season_id
                LEFT JOIN participant_stats ps ON ps.tournament_id = t.id
                LEFT JOIN coverage_stats cs ON cs.tournament_id = t.id
            )
            """
        )


class FederationReportFinanceReconciliation(models.Model):
    _name = "federation.report.finance.reconciliation"
    _description = "Federation Finance Reconciliation Report"
    _auto = False
    _order = "needs_follow_up desc, created_on desc"

    EVENT_TYPE_SELECTION = [
        ("charge", "Charge"),
        ("credit", "Credit"),
        ("reimbursement", "Reimbursement"),
    ]
    STATE_SELECTION = [
        ("draft", "Draft"),
        ("confirmed", "Confirmed"),
        ("settled", "Settled"),
        ("cancelled", "Cancelled"),
    ]
    FOLLOW_UP_SELECTION = [
        ("draft", "Draft"),
        ("awaiting_settlement", "Awaiting Settlement"),
        ("awaiting_reference", "Awaiting Reference"),
        ("complete", "Complete"),
        ("cancelled", "Cancelled"),
    ]

    finance_event_id = fields.Many2one("federation.finance.event", string="Finance Event", readonly=True)
    fee_type_id = fields.Many2one("federation.fee.type", string="Fee Type", readonly=True)
    event_type = fields.Selection(EVENT_TYPE_SELECTION, string="Event Type", readonly=True)
    state = fields.Selection(STATE_SELECTION, string="State", readonly=True)
    created_on = fields.Datetime(string="Created On", readonly=True)
    club_id = fields.Many2one("federation.club", string="Club", readonly=True)
    player_id = fields.Many2one("federation.player", string="Player", readonly=True)
    referee_id = fields.Many2one("federation.referee", string="Referee", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Partner", readonly=True)
    counterparty_display = fields.Char(string="Counterparty", readonly=True)
    source_model = fields.Char(string="Source Model", readonly=True)
    source_res_id = fields.Integer(string="Source Record ID", readonly=True)
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True)
    amount = fields.Monetary(string="Amount", currency_field="currency_id", readonly=True)
    invoice_ref = fields.Char(string="Invoice Ref", readonly=True)
    external_ref = fields.Char(string="External Ref", readonly=True)
    age_days = fields.Integer(string="Age (Days)", readonly=True)
    follow_up_status = fields.Selection(FOLLOW_UP_SELECTION, string="Follow-up Status", readonly=True)
    needs_follow_up = fields.Boolean(string="Needs Follow-up", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE VIEW federation_report_finance_reconciliation AS (
                SELECT
                    fe.id AS id,
                    fe.id AS finance_event_id,
                    fe.fee_type_id,
                    fe.event_type,
                    fe.state,
                    fe.create_date AS created_on,
                    fe.club_id,
                    fe.player_id,
                    fe.referee_id,
                    fe.partner_id,
                    COALESCE(fc.name, fp.name, fr.name, rp.name, '') AS counterparty_display,
                    fe.source_model,
                    fe.source_res_id,
                    fe.currency_id,
                    fe.amount,
                    fe.invoice_ref,
                    fe.external_ref,
                    (CURRENT_DATE - COALESCE(fe.create_date::date, CURRENT_DATE))::int AS age_days,
                    CASE
                        WHEN fe.state = 'cancelled' THEN 'cancelled'
                        WHEN fe.state = 'settled'
                          AND COALESCE(NULLIF(fe.invoice_ref, ''), NULLIF(fe.external_ref, '')) IS NULL THEN 'awaiting_reference'
                        WHEN fe.state = 'settled' THEN 'complete'
                        WHEN fe.state = 'confirmed' THEN 'awaiting_settlement'
                        ELSE 'draft'
                    END AS follow_up_status,
                    CASE
                        WHEN fe.state IN ('draft', 'confirmed') THEN TRUE
                        WHEN fe.state = 'settled'
                          AND COALESCE(NULLIF(fe.invoice_ref, ''), NULLIF(fe.external_ref, '')) IS NULL THEN TRUE
                        ELSE FALSE
                    END AS needs_follow_up
                FROM federation_finance_event fe
                LEFT JOIN federation_club fc ON fc.id = fe.club_id
                LEFT JOIN federation_player fp ON fp.id = fe.player_id
                LEFT JOIN federation_referee fr ON fr.id = fe.referee_id
                LEFT JOIN res_partner rp ON rp.id = fe.partner_id
            )
            """
        )


class FederationReportNotificationException(models.Model):
    _name = "federation.report.notification.exception"
    _description = "Federation Notification Exception Report"
    _auto = False
    _order = "created_on desc, notification_log_id desc"

    NOTIFICATION_TYPE_SELECTION = [
        ("email", "Email"),
        ("activity", "Activity"),
        ("other", "Other"),
    ]

    STATE_SELECTION = [
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    ]

    notification_log_id = fields.Many2one(
        "federation.notification.log",
        string="Notification Log",
        readonly=True,
    )
    created_on = fields.Datetime(string="Created On", readonly=True)
    name = fields.Char(string="Name", readonly=True)
    target_model = fields.Char(string="Target Model", readonly=True)
    target_res_id = fields.Integer(string="Target Record ID", readonly=True)
    recipient_email = fields.Char(string="Recipient Email", readonly=True)
    notification_type = fields.Selection(
        NOTIFICATION_TYPE_SELECTION,
        string="Notification Type",
        readonly=True,
    )
    template_xmlid = fields.Char(string="Template XML ID", readonly=True)
    state = fields.Selection(STATE_SELECTION, string="State", readonly=True)
    message = fields.Text(string="Failure Message", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE VIEW federation_report_notification_exception AS (
                SELECT
                    log.id AS id,
                    log.id AS notification_log_id,
                    log.create_date AS created_on,
                    log.name,
                    log.target_model,
                    log.target_res_id,
                    log.recipient_email,
                    log.notification_type,
                    log.template_xmlid,
                    log.state,
                    log.message
                FROM federation_notification_log log
                WHERE log.state = 'failed'
            )
            """
        )


class FederationReportFinanceException(models.Model):
    _name = "federation.report.finance.exception"
    _description = "Federation Finance Exception Report"
    _auto = False
    _order = "effective_date desc, sanction_id desc"

    ISSUE_TYPE_SELECTION = [
        ("missing_fine_event", "Missing Fine Event"),
    ]

    sanction_id = fields.Many2one("federation.sanction", string="Sanction", readonly=True)
    case_id = fields.Many2one(
        "federation.disciplinary.case",
        string="Case",
        readonly=True,
    )
    case_reference = fields.Char(string="Case Reference", readonly=True)
    player_id = fields.Many2one("federation.player", string="Player", readonly=True)
    club_id = fields.Many2one("federation.club", string="Club", readonly=True)
    referee_id = fields.Many2one("federation.referee", string="Referee", readonly=True)
    expected_fee_type_id = fields.Many2one(
        "federation.fee.type",
        string="Expected Fee Type",
        readonly=True,
    )
    effective_date = fields.Date(string="Effective Date", readonly=True)
    expected_amount = fields.Monetary(
        string="Expected Amount",
        currency_field="currency_id",
        readonly=True,
    )
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True)
    issue_type = fields.Selection(ISSUE_TYPE_SELECTION, string="Issue Type", readonly=True)
    issue_note = fields.Text(string="Issue Note", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE VIEW federation_report_finance_exception AS (
                WITH discipline_fee AS (
                    SELECT id, default_amount
                    FROM federation_fee_type
                    WHERE code = 'discipline_fine'
                    LIMIT 1
                )
                SELECT
                    row_number() OVER (
                        ORDER BY COALESCE(s.effective_date, c.decided_on, c.opened_on) DESC, s.id DESC
                    ) AS id,
                    s.id AS sanction_id,
                    s.case_id,
                    c.reference AS case_reference,
                    COALESCE(s.player_id, c.subject_player_id) AS player_id,
                    COALESCE(s.club_id, c.subject_club_id) AS club_id,
                    COALESCE(s.referee_id, c.subject_referee_id) AS referee_id,
                    df.id AS expected_fee_type_id,
                    COALESCE(s.effective_date, c.decided_on, c.opened_on) AS effective_date,
                    CASE
                        WHEN COALESCE(s.amount, 0) = 0 THEN COALESCE(df.default_amount, 0)
                        ELSE s.amount
                    END AS expected_amount,
                    s.currency_id,
                    'missing_fine_event' AS issue_type,
                    'Fine sanction has no linked finance event.' AS issue_note
                FROM federation_sanction s
                JOIN federation_disciplinary_case c ON c.id = s.case_id
                LEFT JOIN discipline_fee df ON TRUE
                LEFT JOIN federation_finance_event fe
                  ON fe.source_model = 'federation.sanction'
                 AND fe.source_res_id = s.id
                 AND (df.id IS NULL OR fe.fee_type_id = df.id)
                WHERE s.sanction_type = 'fine'
                  AND fe.id IS NULL
            )
            """
        )


class FederationReportWorkflowException(models.Model):
    _name = "federation.report.workflow.exception"
    _description = "Federation Workflow Exception Report"
    _auto = False
    _order = "age_days desc, raised_on asc"

    EXCEPTION_TYPE_SELECTION = [
        ("result_submission_stalled", "Result Verification Backlog"),
        ("result_approval_stalled", "Result Approval Backlog"),
        ("override_review_stalled", "Override Review Backlog"),
        ("override_implementation_stalled", "Override Implementation Backlog"),
    ]

    season_id = fields.Many2one("federation.season", string="Season", readonly=True)
    tournament_id = fields.Many2one("federation.tournament", string="Tournament", readonly=True)
    match_id = fields.Many2one("federation.match", string="Match", readonly=True)
    override_request_id = fields.Many2one(
        "federation.override.request",
        string="Override Request",
        readonly=True,
    )
    source_model = fields.Char(string="Source Model", readonly=True)
    source_res_id = fields.Integer(string="Source Record ID", readonly=True)
    reference_name = fields.Char(string="Reference", readonly=True)
    state = fields.Char(string="State", readonly=True)
    responsible_user_id = fields.Many2one(
        "res.users",
        string="Responsible User",
        readonly=True,
    )
    raised_on = fields.Datetime(string="Raised On", readonly=True)
    age_days = fields.Integer(string="Age (Days)", readonly=True)
    exception_type = fields.Selection(
        EXCEPTION_TYPE_SELECTION,
        string="Exception Type",
        readonly=True,
    )
    exception_note = fields.Text(string="Exception Note", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE VIEW federation_report_workflow_exception AS (
                WITH queue AS (
                    SELECT
                        se.id AS season_id,
                        t.id AS tournament_id,
                        m.id AS match_id,
                        NULL::integer AS override_request_id,
                        'federation.match'::varchar AS source_model,
                        m.id AS source_res_id,
                        m.name AS reference_name,
                        m.result_state::varchar AS state,
                        m.result_submitted_by_id AS responsible_user_id,
                        m.result_submitted_on AS raised_on,
                        (CURRENT_DATE - m.result_submitted_on::date)::int AS age_days,
                        'result_submission_stalled'::varchar AS exception_type,
                        'Submitted result is still waiting for verification.'::text AS exception_note
                    FROM federation_match m
                    LEFT JOIN federation_tournament t ON t.id = m.tournament_id
                    LEFT JOIN federation_season se ON se.id = t.season_id
                    WHERE m.result_state = 'submitted'
                      AND m.result_submitted_on IS NOT NULL
                      AND m.result_submitted_on <= (NOW() - INTERVAL '2 day')

                    UNION ALL

                    SELECT
                        se.id AS season_id,
                        t.id AS tournament_id,
                        m.id AS match_id,
                        NULL::integer AS override_request_id,
                        'federation.match'::varchar AS source_model,
                        m.id AS source_res_id,
                        m.name AS reference_name,
                        m.result_state::varchar AS state,
                        m.result_verified_by_id AS responsible_user_id,
                        m.result_verified_on AS raised_on,
                        (CURRENT_DATE - m.result_verified_on::date)::int AS age_days,
                        'result_approval_stalled'::varchar AS exception_type,
                        'Verified result is still waiting for approval.'::text AS exception_note
                    FROM federation_match m
                    LEFT JOIN federation_tournament t ON t.id = m.tournament_id
                    LEFT JOIN federation_season se ON se.id = t.season_id
                    WHERE m.result_state = 'verified'
                      AND m.result_verified_on IS NOT NULL
                      AND m.result_verified_on <= (NOW() - INTERVAL '2 day')

                    UNION ALL

                    SELECT
                        NULL::integer AS season_id,
                        NULL::integer AS tournament_id,
                        NULL::integer AS match_id,
                        req.id AS override_request_id,
                        'federation.override.request'::varchar AS source_model,
                        req.id AS source_res_id,
                        req.name AS reference_name,
                        req.state::varchar AS state,
                        req.requested_by_id AS responsible_user_id,
                        req.requested_on AS raised_on,
                        (CURRENT_DATE - req.requested_on::date)::int AS age_days,
                        'override_review_stalled'::varchar AS exception_type,
                        'Submitted override request is still waiting for governance review.'::text AS exception_note
                    FROM federation_override_request req
                    WHERE req.state = 'submitted'
                      AND req.requested_on <= (NOW() - INTERVAL '3 day')

                    UNION ALL

                    SELECT
                        NULL::integer AS season_id,
                        NULL::integer AS tournament_id,
                        NULL::integer AS match_id,
                        req.id AS override_request_id,
                        'federation.override.request'::varchar AS source_model,
                        req.id AS source_res_id,
                        req.name AS reference_name,
                        req.state::varchar AS state,
                        req.requested_by_id AS responsible_user_id,
                        req.requested_on AS raised_on,
                        (CURRENT_DATE - req.requested_on::date)::int AS age_days,
                        'override_implementation_stalled'::varchar AS exception_type,
                        'Approved override request is still waiting to be implemented.'::text AS exception_note
                    FROM federation_override_request req
                    WHERE req.state = 'approved'
                      AND req.requested_on <= (NOW() - INTERVAL '3 day')
                )
                SELECT
                    row_number() OVER (
                        ORDER BY age_days DESC, raised_on ASC, source_model ASC, source_res_id ASC
                    ) AS id,
                    queue.season_id,
                    queue.tournament_id,
                    queue.match_id,
                    queue.override_request_id,
                    queue.source_model,
                    queue.source_res_id,
                    queue.reference_name,
                    queue.state,
                    queue.responsible_user_id,
                    queue.raised_on,
                    queue.age_days,
                    queue.exception_type,
                    queue.exception_note
                FROM queue
            )
            """
        )


class FederationReportSeasonChecklist(models.Model):
    _name = "federation.report.season.checklist"
    _description = "Federation Season Checklist Report"
    _auto = False
    _order = "season_id"

    STATUS_SELECTION = FederationReportOperational.STATUS_SELECTION

    season_id = fields.Many2one("federation.season", string="Season", readonly=True)
    season_state = fields.Char(string="Season State", readonly=True)
    draft_season_registration_count = fields.Integer(
        string="Draft Season Registrations",
        readonly=True,
    )
    submitted_season_registration_count = fields.Integer(
        string="Submitted Season Registrations",
        readonly=True,
    )
    draft_tournament_registration_count = fields.Integer(
        string="Draft Tournament Registrations",
        readonly=True,
    )
    submitted_tournament_registration_count = fields.Integer(
        string="Submitted Tournament Registrations",
        readonly=True,
    )
    live_tournament_count = fields.Integer(string="Live Tournaments", readonly=True)
    published_tournament_count = fields.Integer(
        string="Published Tournaments",
        readonly=True,
    )
    unpublished_tournament_count = fields.Integer(
        string="Unpublished Tournaments",
        readonly=True,
    )
    workflow_exception_count = fields.Integer(
        string="Workflow Exceptions",
        readonly=True,
    )
    checklist_status = fields.Selection(
        STATUS_SELECTION,
        string="Checklist Status",
        readonly=True,
    )
    checklist_note = fields.Text(string="Checklist Note", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE VIEW federation_report_season_checklist AS (
                WITH season_registration_stats AS (
                    SELECT
                        reg.season_id,
                        COUNT(*) FILTER (WHERE reg.state = 'draft') AS draft_season_registration_count,
                        COUNT(*) FILTER (WHERE reg.state = 'submitted') AS submitted_season_registration_count
                    FROM federation_season_registration reg
                    GROUP BY reg.season_id
                ),
                tournament_registration_stats AS (
                    SELECT
                        t.season_id,
                        COUNT(*) FILTER (WHERE reg.state = 'draft') AS draft_tournament_registration_count,
                        COUNT(*) FILTER (WHERE reg.state = 'submitted') AS submitted_tournament_registration_count
                    FROM federation_tournament_registration reg
                    JOIN federation_tournament t ON t.id = reg.tournament_id
                    GROUP BY t.season_id
                ),
                tournament_stats AS (
                    SELECT
                        t.season_id,
                        COUNT(*) FILTER (WHERE t.state IN ('open', 'in_progress')) AS live_tournament_count,
                        COUNT(*) FILTER (WHERE COALESCE(t.website_published, FALSE)) AS published_tournament_count,
                        COUNT(*) FILTER (WHERE NOT COALESCE(t.website_published, FALSE)) AS unpublished_tournament_count
                    FROM federation_tournament t
                    GROUP BY t.season_id
                ),
                workflow_stats AS (
                    SELECT
                        queue.season_id,
                        COUNT(*) AS workflow_exception_count
                    FROM (
                        SELECT t.season_id
                        FROM federation_match m
                        JOIN federation_tournament t ON t.id = m.tournament_id
                        WHERE (
                            (m.result_state = 'submitted' AND m.result_submitted_on IS NOT NULL AND m.result_submitted_on <= (NOW() - INTERVAL '2 day'))
                            OR (m.result_state = 'verified' AND m.result_verified_on IS NOT NULL AND m.result_verified_on <= (NOW() - INTERVAL '2 day'))
                        )

                        UNION ALL

                        SELECT t.season_id
                        FROM federation_override_request req
                        JOIN federation_tournament t
                          ON req.target_model = 'federation.tournament'
                         AND req.target_res_id = t.id
                        WHERE (
                            (req.state = 'submitted' AND req.requested_on <= (NOW() - INTERVAL '3 day'))
                            OR (req.state = 'approved' AND req.requested_on <= (NOW() - INTERVAL '3 day'))
                        )
                    ) queue
                    GROUP BY queue.season_id
                )
                SELECT
                    row_number() OVER (ORDER BY s.id) AS id,
                    s.id AS season_id,
                    s.state::varchar AS season_state,
                    COALESCE(srs.draft_season_registration_count, 0) AS draft_season_registration_count,
                    COALESCE(srs.submitted_season_registration_count, 0) AS submitted_season_registration_count,
                    COALESCE(trs.draft_tournament_registration_count, 0) AS draft_tournament_registration_count,
                    COALESCE(trs.submitted_tournament_registration_count, 0) AS submitted_tournament_registration_count,
                    COALESCE(ts.live_tournament_count, 0) AS live_tournament_count,
                    COALESCE(ts.published_tournament_count, 0) AS published_tournament_count,
                    COALESCE(ts.unpublished_tournament_count, 0) AS unpublished_tournament_count,
                    COALESCE(ws.workflow_exception_count, 0) AS workflow_exception_count,
                    CASE
                        WHEN COALESCE(srs.submitted_season_registration_count, 0) > 0
                          OR COALESCE(trs.submitted_tournament_registration_count, 0) > 0
                          OR COALESCE(ws.workflow_exception_count, 0) > 0
                        THEN 'blocked'
                        WHEN COALESCE(srs.draft_season_registration_count, 0) > 0
                          OR COALESCE(trs.draft_tournament_registration_count, 0) > 0
                          OR (
                              COALESCE(ts.live_tournament_count, 0) > 0
                              AND COALESCE(ts.unpublished_tournament_count, 0) > 0
                          )
                        THEN 'attention'
                        ELSE 'healthy'
                    END AS checklist_status,
                    CASE
                        WHEN COALESCE(srs.submitted_season_registration_count, 0) > 0 THEN 'Season registrations are waiting for staff review.'
                        WHEN COALESCE(trs.submitted_tournament_registration_count, 0) > 0 THEN 'Tournament registrations are waiting for staff review.'
                        WHEN COALESCE(ws.workflow_exception_count, 0) > 0 THEN 'Workflow exceptions must be cleared before seasonal operations are considered healthy.'
                        WHEN COALESCE(srs.draft_season_registration_count, 0) > 0 THEN 'Draft season registrations still need operator follow-up.'
                        WHEN COALESCE(trs.draft_tournament_registration_count, 0) > 0 THEN 'Draft tournament registrations still need operator follow-up.'
                        WHEN COALESCE(ts.live_tournament_count, 0) > 0 AND COALESCE(ts.unpublished_tournament_count, 0) > 0 THEN 'Some live tournaments are not yet published on the public site.'
                        ELSE 'Season operations checklist is currently clear.'
                    END AS checklist_note
                FROM federation_season s
                LEFT JOIN season_registration_stats srs ON srs.season_id = s.id
                LEFT JOIN tournament_registration_stats trs ON trs.season_id = s.id
                LEFT JOIN tournament_stats ts ON ts.season_id = s.id
                LEFT JOIN workflow_stats ws ON ws.season_id = s.id
            )
            """
        )