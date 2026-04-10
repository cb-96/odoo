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