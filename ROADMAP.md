# Sports Federation Platform Roadmap

## Strategic objective

Build the project in stages from:  
**(1) stable federation operations** → **(2) automation and rule enforcement** → **(3) federation intelligence and self-service** → **(4) long-term platform maturity**. This sequence fits the current architecture, which already centers on `base`, `tournament`, `competition_engine`, `people`, `rosters`, `officiating`, `result_control`, `standings`, `portal`, and `public_site`, with clearly documented workflows for tournaments, match day, results, discipline, compliance, finance, governance, and imports. See: [CONTEXT](CONTEXT.md), [TECHNICAL_NOTE](TECHNICAL_NOTE.md), [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md), [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md), [_workflows/WORKFLOW_RESULT_PIPELINE.md](_workflows/WORKFLOW_RESULT_PIPELINE.md), [_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md](_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md), [_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md](_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md), [_workflows/WORKFLOW_FINANCIAL_TRACKING.md](_workflows/WORKFLOW_FINANCIAL_TRACKING.md), [_workflows/WORKFLOW_GOVERNANCE_OVERRIDE.md](_workflows/WORKFLOW_GOVERNANCE_OVERRIDE.md), [_workflows/WORKFLOW_DATA_IMPORT.md](_workflows/WORKFLOW_DATA_IMPORT.md), [_workflows/WORKFLOW_PUBLIC_PUBLICATION.md](_workflows/WORKFLOW_PUBLIC_PUBLICATION.md)

# Phase 1 — Stabilize and standardize the current platform

## Goal

Turn the current implementation into a **predictable operational baseline** by making rules, states, and blocking conditions explicit and consistent across modules. The current workflows are already strong and realistic, but several rules are still described narratively and should be formalized as platform policy. See: [TECHNICAL_NOTE](TECHNICAL_NOTE.md), [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_RESULT_PIPELINE.md](_workflows/WORKFLOW_RESULT_PIPELINE.md)

## Main outcomes

*   One authoritative **state and ownership matrix** for the main business objects. See: [TECHNICAL_NOTE](TECHNICAL_NOTE.md), [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md), [_workflows/WORKFLOW_RESULT_PIPELINE.md](_workflows/WORKFLOW_RESULT_PIPELINE.md)
*   One authoritative **blocking vs warning matrix** across registration, compliance, rosters, match day, results, and publication. See: [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md](_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md), [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md), [_workflows/WORKFLOW_RESULT_PIPELINE.md](_workflows/WORKFLOW_RESULT_PIPELINE.md), [_workflows/WORKFLOW_PUBLIC_PUBLICATION.md](_workflows/WORKFLOW_PUBLIC_PUBLICATION.md)
*   Stronger consistency between workflows and actual module behavior. See: [TECHNICAL_NOTE](TECHNICAL_NOTE.md), [CONTEXT](CONTEXT.md)

## Workstreams

### 1.1 Normalize lifecycle and source-of-truth rules

Define centrally, for each core object:

*   who owns the lifecycle,
*   which downstream modules consume it,
*   which states are official,
*   and which states are terminal or reversible. This is especially important for results, standings, registrations, and discipline. See: [TECHNICAL_NOTE](TECHNICAL_NOTE.md), [_workflows/WORKFLOW_RESULT_PIPELINE.md](_workflows/WORKFLOW_RESULT_PIPELINE.md), [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md](_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md)

**Priority examples**

*   Results: only approved results should count for standings and public publication. See: [_workflows/WORKFLOW_RESULT_PIPELINE.md](_workflows/WORKFLOW_RESULT_PIPELINE.md), [_workflows/WORKFLOW_PUBLIC_PUBLICATION.md](_workflows/WORKFLOW_PUBLIC_PUBLICATION.md)
*   Standings: define whether they can be frozen, republished, or manually corrected after correction/appeal. See: [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md), [_workflows/WORKFLOW_RESULT_PIPELINE.md](_workflows/WORKFLOW_RESULT_PIPELINE.md), [TECHNICAL_NOTE](TECHNICAL_NOTE.md)
*   Registrations: define whether unpaid fees are advisory or blocking by competition policy. See: [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_FINANCIAL_TRACKING.md](_workflows/WORKFLOW_FINANCIAL_TRACKING.md)

### 1.2 Create a blocking-policy matrix

Explicitly classify checks as:

*   **hard blockers** (action cannot continue), or
*   **warnings** (action continues but is flagged). See: [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md), [_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md](_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md), [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md)

**Priority examples**

*   Missing compliance documents before registration approval. See: [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md](_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md)
*   License validity and active suspensions on match sheets. See: [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md), [_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md](_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md)
*   Approved-result requirement before public publication. See: [_workflows/WORKFLOW_RESULT_PIPELINE.md](_workflows/WORKFLOW_RESULT_PIPELINE.md), [_workflows/WORKFLOW_PUBLIC_PUBLICATION.md](_workflows/WORKFLOW_PUBLIC_PUBLICATION.md)

### 1.3 Data governance and import standardization

Make stable unique codes mandatory for all externally referenceable objects used in imports and matching, especially:

*   clubs,
*   teams,
*   tournaments,
*   potentially players where needed. The import workflow already assumes strong matching keys and idempotent behavior; formalizing this improves long-term data quality. See: [_workflows/WORKFLOW_DATA_IMPORT.md](_workflows/WORKFLOW_DATA_IMPORT.md), [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md)

## Deliverables

*   `STATE_AND_OWNERSHIP_MATRIX.md` — see: [TECHNICAL_NOTE](TECHNICAL_NOTE.md), [_workflows/WORKFLOW_RESULT_PIPELINE.md](_workflows/WORKFLOW_RESULT_PIPELINE.md)
*   `BLOCKING_POLICY_MATRIX.md` — see: [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md](_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md), [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md)
*   `DATA_GOVERNANCE.md` for stable identifiers and import matching rules. See: [_workflows/WORKFLOW_DATA_IMPORT.md](_workflows/WORKFLOW_DATA_IMPORT.md), [TECHNICAL_NOTE](TECHNICAL_NOTE.md)

## Success criteria

*   Admin users can explain exactly what blocks what. See: [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md), [_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md](_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md)
*   No ambiguity remains around when a result, standing, registration, or compliance record becomes official. See: [_workflows/WORKFLOW_RESULT_PIPELINE.md](_workflows/WORKFLOW_RESULT_PIPELINE.md), [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md), [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md)
*   Import behavior is deterministic and safe. See: [_workflows/WORKFLOW_DATA_IMPORT.md](_workflows/WORKFLOW_DATA_IMPORT.md)

***

# Phase 2 — Operational automation

## Goal

Reduce manual federation workload by turning important workflow steps into **default automations**, while keeping review and governance controls in place. The current documentation often describes a framework plus extension point; this phase turns those extension points into standard operational behaviors. See: [_workflows/WORKFLOW_FINANCIAL_TRACKING.md](_workflows/WORKFLOW_FINANCIAL_TRACKING.md), [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md), [_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md](_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md)

## Main outcomes

*   Finance events created automatically from key business actions. See: [_workflows/WORKFLOW_FINANCIAL_TRACKING.md](_workflows/WORKFLOW_FINANCIAL_TRACKING.md), [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md](_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md)
*   Notifications triggered by state transitions, not just periodic checks. See: [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md](_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md), [_workflows/WORKFLOW_FINANCIAL_TRACKING.md](_workflows/WORKFLOW_FINANCIAL_TRACKING.md)
*   Stage progression partly automated from standings and tournament rules. See: [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md), [_workflows/WORKFLOW_RESULT_PIPELINE.md](_workflows/WORKFLOW_RESULT_PIPELINE.md)

## Workstreams

### 2.1 Finance-event automation

The finance workflow already defines fee types and finance events, but many auto-creations are still described as “extendable.” Convert the highest-value ones into standard defaults:

*   season registration approval → registration fee event (see [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md) and [_workflows/WORKFLOW_FINANCIAL_TRACKING.md](_workflows/WORKFLOW_FINANCIAL_TRACKING.md))
*   player license issuance → license fee event (see [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md) and [_workflows/WORKFLOW_FINANCIAL_TRACKING.md](_workflows/WORKFLOW_FINANCIAL_TRACKING.md))
*   sanction/fine creation → finance event (see [_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md](_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md) and [_workflows/WORKFLOW_FINANCIAL_TRACKING.md](_workflows/WORKFLOW_FINANCIAL_TRACKING.md))
*   referee assignment completion → reimbursement event (see [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md) and [_workflows/WORKFLOW_FINANCIAL_TRACKING.md](_workflows/WORKFLOW_FINANCIAL_TRACKING.md))

### 2.2 Event-driven notification framework

Right now notifications are referenced in season registration and compliance, but the platform should move toward state-driven communication:

*   submitted registration → confirmation/reminder (see [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md))
*   missing or expiring compliance document → renewal notice (see [_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md](_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md))
*   referee assigned but not confirmed → reminder/escalation (see [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md))
*   verified result awaiting approval → internal activity or escalation (see [_workflows/WORKFLOW_RESULT_PIPELINE.md](_workflows/WORKFLOW_RESULT_PIPELINE.md))

### 2.3 Assisted stage progression

Tournament lifecycle already describes manual review of standings to determine qualifiers. Add assisted workflows that:

*   propose qualifiers based on standings (see [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md) and [_workflows/WORKFLOW_RESULT_PIPELINE.md](_workflows/WORKFLOW_RESULT_PIPELINE.md))
*   create next-stage participants (see [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md))
*   and optionally launch the schedule generation wizard prefilled with the right input (see [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md) and [TECHNICAL_NOTE](TECHNICAL_NOTE.md))

## Deliverables

*   Auto-event creation hooks in `finance_bridge` (see [_workflows/WORKFLOW_FINANCIAL_TRACKING.md](_workflows/WORKFLOW_FINANCIAL_TRACKING.md)).
*   Notification trigger matrix + scheduler/event logic (see [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md](_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md), [_workflows/WORKFLOW_FINANCIAL_TRACKING.md](_workflows/WORKFLOW_FINANCIAL_TRACKING.md)).
*   Qualification assistant / stage progression wizard (see [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md) and [_workflows/WORKFLOW_RESULT_PIPELINE.md](_workflows/WORKFLOW_RESULT_PIPELINE.md)).

## Success criteria

*   Fewer manual finance entries after normal registration/discipline/officiating flows (see [_workflows/WORKFLOW_FINANCIAL_TRACKING.md](_workflows/WORKFLOW_FINANCIAL_TRACKING.md), [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md](_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md), [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md)).
*   Fewer stale records due to missed follow-up (see [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md](_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md)).
*   Less manual tournament administration between stages (see [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md)).

***

# Phase 3 — Unified eligibility and competition intelligence

## Goal

Move from “workflow support” to **rule-based decision support** by centralizing eligibility and competition logic.

## Main outcomes

*   One authoritative eligibility engine (see [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md), [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md](_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md), [_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md](_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md)).
*   Stronger rules-driven use of rosters, licenses, compliance, suspensions, and competition rules (see [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md), [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md), [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md)).
*   More automatic and explainable qualification/standing behavior (see [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md), [_workflows/WORKFLOW_RESULT_PIPELINE.md](_workflows/WORKFLOW_RESULT_PIPELINE.md)).

## Workstreams

### 3.1 Unified eligibility engine

This is the highest-value new feature in the roadmap. Eligibility is currently implied across licenses, rosters, suspensions, compliance, and rules (see [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md), [_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md](_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md), [TECHNICAL_NOTE](TECHNICAL_NOTE.md)).

Create a central service that answers:

*   Can this player appear on a roster? (see [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md), [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md))
*   Can this player appear on this match sheet? (see [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md), [_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md](_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md))
*   Can this team or club register for this competition? (see [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md](_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md))
*   What exact rule or missing artifact is blocking the operation? (see [_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md](_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md), [_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md](_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md), [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md))

### 3.2 Explainable standings and qualification

Standings already use rules, points, tie-breakers, and publication controls. Expand this into a more explainable engine that can:

*   expose which tie-break rule determined the ranking (see [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md), [_workflows/WORKFLOW_RESULT_PIPELINE.md](_workflows/WORKFLOW_RESULT_PIPELINE.md)),
*   flag qualifiers/eliminations explicitly (see [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md)),
*   and show why a team progressed or was excluded (see [_workflows/WORKFLOW_RESULT_PIPELINE.md](_workflows/WORKFLOW_RESULT_PIPELINE.md), [_workflows/WORKFLOW_GOVERNANCE_OVERRIDE.md](_workflows/WORKFLOW_GOVERNANCE_OVERRIDE.md)).

### 3.3 Sanction impact automation

Discipline already describes sanctions such as fines, bans, and point deductions, but impact propagation should become automatic:

*   fine → finance event (see [_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md](_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md), [_workflows/WORKFLOW_FINANCIAL_TRACKING.md](_workflows/WORKFLOW_FINANCIAL_TRACKING.md)),
*   suspension → player ineligible on match sheet (see [_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md](_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md), [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md)),
*   point deduction → standings adjustment through a governed mechanism (see [_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md](_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md), [_workflows/WORKFLOW_GOVERNANCE_OVERRIDE.md](_workflows/WORKFLOW_GOVERNANCE_OVERRIDE.md)).

## Deliverables

*   `eligibility_service` and explainable blocking messages (see [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md), [_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md](_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md), [_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md](_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md), [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md)).
*   standings reason/explanation layer (see [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md), [_workflows/WORKFLOW_RESULT_PIPELINE.md](_workflows/WORKFLOW_RESULT_PIPELINE.md)).
*   sanction effect propagation rules (see [_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md](_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md), [_workflows/WORKFLOW_FINANCIAL_TRACKING.md](_workflows/WORKFLOW_FINANCIAL_TRACKING.md), [_workflows/WORKFLOW_GOVERNANCE_OVERRIDE.md](_workflows/WORKFLOW_GOVERNANCE_OVERRIDE.md)).

## Success criteria

*   Admins stop manually interpreting multiple modules to decide eligibility (see [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md), [_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md](_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md), [_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md](_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md), [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md)).
*   Standing and qualification outcomes become auditable and explainable (see [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md), [_workflows/WORKFLOW_RESULT_PIPELINE.md](_workflows/WORKFLOW_RESULT_PIPELINE.md), [_workflows/WORKFLOW_GOVERNANCE_OVERRIDE.md](_workflows/WORKFLOW_GOVERNANCE_OVERRIDE.md)).
*   Discipline decisions produce automatic operational effects (see [_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md](_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md), [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md), [_workflows/WORKFLOW_FINANCIAL_TRACKING.md](_workflows/WORKFLOW_FINANCIAL_TRACKING.md)).

***

# Phase 4 — Self-service and public experience

## Goal

Make the platform significantly more useful for clubs, referees, and the public without weakening governance or security.

## Main outcomes

*   Stronger club self-service in portal flows (see [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [CONTEXT](CONTEXT.md)).
*   Referee self-service tools for operational confirmation and reporting (see [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md)).
*   Richer public competition experience (see [_workflows/WORKFLOW_PUBLIC_PUBLICATION.md](_workflows/WORKFLOW_PUBLIC_PUBLICATION.md)).

## Workstreams

### 4.1 Club portal dashboard

Build a structured portal workspace for club representatives:

*   season registration status (see [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md)),
*   missing compliance documents (see [_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md](_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md)),
*   outstanding finance events (see [_workflows/WORKFLOW_FINANCIAL_TRACKING.md](_workflows/WORKFLOW_FINANCIAL_TRACKING.md)),
*   upcoming matches and team obligations (see [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md), [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md)),
*   governance/discipline items affecting the club (see [_workflows/WORKFLOW_GOVERNANCE_OVERRIDE.md](_workflows/WORKFLOW_GOVERNANCE_OVERRIDE.md), [_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md](_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md)).

### 4.2 Referee workspace

Build an officiating-facing self-service area where referees can:

*   confirm assignments (see [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md)),
*   report incidents (see [_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md](_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md), [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md)),
*   review match details and venue data (see [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md), [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md)),
*   and eventually submit reimbursement claims (see [_workflows/WORKFLOW_FINANCIAL_TRACKING.md](_workflows/WORKFLOW_FINANCIAL_TRACKING.md), [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md)).

### 4.3 Public competition enhancement

Public publication is already good, but the next step is richer usability:

*   filterable schedules/results (see [_workflows/WORKFLOW_PUBLIC_PUBLICATION.md](_workflows/WORKFLOW_PUBLIC_PUBLICATION.md), [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md)),
*   seasonal archives (see [_workflows/WORKFLOW_PUBLIC_PUBLICATION.md](_workflows/WORKFLOW_PUBLIC_PUBLICATION.md), [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md)),
*   team pages or competition pages with grouped views by stage/group (see [_workflows/WORKFLOW_PUBLIC_PUBLICATION.md](_workflows/WORKFLOW_PUBLIC_PUBLICATION.md), [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md)),
*   downloadable reports or result summaries where useful (see [_workflows/WORKFLOW_RESULT_PIPELINE.md](_workflows/WORKFLOW_RESULT_PIPELINE.md), [_workflows/WORKFLOW_PUBLIC_PUBLICATION.md](_workflows/WORKFLOW_PUBLIC_PUBLICATION.md)).

## Deliverables

*   Portal dashboard pages (see [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md](_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md), [_workflows/WORKFLOW_FINANCIAL_TRACKING.md](_workflows/WORKFLOW_FINANCIAL_TRACKING.md)).
*   Referee portal / self-service flows (see [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md), [_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md](_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md)).
*   Public page enhancements and archives (see [_workflows/WORKFLOW_PUBLIC_PUBLICATION.md](_workflows/WORKFLOW_PUBLIC_PUBLICATION.md), [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md)).

## Success criteria

*   Clubs can resolve more issues without federation staff intervention (see [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md](_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md), [_workflows/WORKFLOW_FINANCIAL_TRACKING.md](_workflows/WORKFLOW_FINANCIAL_TRACKING.md)).
*   Referee coordination becomes less manual (see [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md)).
*   Public site becomes a genuine competition information hub (see [_workflows/WORKFLOW_PUBLIC_PUBLICATION.md](_workflows/WORKFLOW_PUBLIC_PUBLICATION.md)).

***

# Phase 5 — Reporting, analytics, and federation management intelligence

## Goal

Turn the project into a true federation decision-support platform.

## Main outcomes

*   Better operational KPIs (see [_workflows/WORKFLOW_FINANCIAL_TRACKING.md](_workflows/WORKFLOW_FINANCIAL_TRACKING.md), [_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md](_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md), [_workflows/WORKFLOW_GOVERNANCE_OVERRIDE.md](_workflows/WORKFLOW_GOVERNANCE_OVERRIDE.md), [_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md](_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md)).
*   Better visibility into process bottlenecks and recurring risk areas (see [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_DATA_IMPORT.md](_workflows/WORKFLOW_DATA_IMPORT.md), [_workflows/WORKFLOW_RESULT_PIPELINE.md](_workflows/WORKFLOW_RESULT_PIPELINE.md)).
*   Better strategic oversight across seasons (see [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md)).

## Workstreams

### 5.1 Federation KPI layer

Add dashboards/reports for:

*   late registrations by club and season (see [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_DATA_IMPORT.md](_workflows/WORKFLOW_DATA_IMPORT.md)),
*   document failure/expiry rates by requirement (see [_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md](_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md)),
*   contested and corrected result frequency (see [_workflows/WORKFLOW_RESULT_PIPELINE.md](_workflows/WORKFLOW_RESULT_PIPELINE.md)),
*   referee coverage and assignment balance (see [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md)),
*   sanctions, appeals, and override volume (see [_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md](_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md), [_workflows/WORKFLOW_GOVERNANCE_OVERRIDE.md](_workflows/WORKFLOW_GOVERNANCE_OVERRIDE.md)),
*   finance event aging and outstanding balances (see [_workflows/WORKFLOW_FINANCIAL_TRACKING.md](_workflows/WORKFLOW_FINANCIAL_TRACKING.md)).

### 5.2 Historical analytics and season rollover

Add structured end-of-season capabilities:

*   archive final standings and public pages (see [_workflows/WORKFLOW_PUBLIC_PUBLICATION.md](_workflows/WORKFLOW_PUBLIC_PUBLICATION.md), [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md)),
*   clone structures into the next season (see [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md)),
*   preserve club/player/referee historical traces (see [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md](_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md), [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md)).

### 5.3 Data quality monitoring

Use the import and governance foundations to add:

*   duplicate candidate detection (see [_workflows/WORKFLOW_DATA_IMPORT.md](_workflows/WORKFLOW_DATA_IMPORT.md)),
*   missing-code / invalid-reference diagnostics (see [_workflows/WORKFLOW_DATA_IMPORT.md](_workflows/WORKFLOW_DATA_IMPORT.md), [TECHNICAL_NOTE](TECHNICAL_NOTE.md)),
*   orphan record checks and cleanup reports (see [_workflows/WORKFLOW_DATA_IMPORT.md](_workflows/WORKFLOW_DATA_IMPORT.md), [TECHNICAL_NOTE](TECHNICAL_NOTE.md)).

## Deliverables

*   KPI report suite (see [_workflows/WORKFLOW_FINANCIAL_TRACKING.md](_workflows/WORKFLOW_FINANCIAL_TRACKING.md), [_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md](_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md), [_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md](_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md), [_workflows/WORKFLOW_GOVERNANCE_OVERRIDE.md](_workflows/WORKFLOW_GOVERNANCE_OVERRIDE.md)).
*   season rollover toolkit (see [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md)).
*   data quality dashboard (see [_workflows/WORKFLOW_DATA_IMPORT.md](_workflows/WORKFLOW_DATA_IMPORT.md), [TECHNICAL_NOTE](TECHNICAL_NOTE.md)).

## Success criteria

*   Federation leadership can monitor health of operations across seasons (see [_workflows/WORKFLOW_FINANCIAL_TRACKING.md](_workflows/WORKFLOW_FINANCIAL_TRACKING.md), [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md](_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md)).
*   Historical data becomes reusable rather than archival-only (see [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md)).
*   Data cleanup becomes proactive rather than reactive (see [_workflows/WORKFLOW_DATA_IMPORT.md](_workflows/WORKFLOW_DATA_IMPORT.md), [TECHNICAL_NOTE](TECHNICAL_NOTE.md)).

***

# Cross-cutting work that should happen throughout the roadmap

## A) Testing and quality gates

The technical note already emphasizes tests, CI, and deterministic behavior, especially around schedule generation. Keep expanding that throughout every phase:

*   unit tests for rule-heavy services (see [TECHNICAL_NOTE](TECHNICAL_NOTE.md))
*   integration tests for workflows (see [TECHNICAL_NOTE](TECHNICAL_NOTE.md))
*   public/portal behavior tests for safe exposure (see [_workflows/WORKFLOW_PUBLIC_PUBLICATION.md](_workflows/WORKFLOW_PUBLIC_PUBLICATION.md), [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [TECHNICAL_NOTE](TECHNICAL_NOTE.md))

## B) Performance and scaling

The technical note already highlights indexing, batching, `read_group`, and cron/background processing for larger workloads. Profile and harden:

*   standings recompute (see [TECHNICAL_NOTE](TECHNICAL_NOTE.md), [_workflows/WORKFLOW_RESULT_PIPELINE.md](_workflows/WORKFLOW_RESULT_PIPELINE.md))
*   bulk fixture generation (see [TECHNICAL_NOTE](TECHNICAL_NOTE.md), [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md))
*   compliance scans (see [TECHNICAL_NOTE](TECHNICAL_NOTE.md), [_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md](_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md))
*   import batches (see [TECHNICAL_NOTE](TECHNICAL_NOTE.md), [_workflows/WORKFLOW_DATA_IMPORT.md](_workflows/WORKFLOW_DATA_IMPORT.md))
*   public pages (see [TECHNICAL_NOTE](TECHNICAL_NOTE.md), [_workflows/WORKFLOW_PUBLIC_PUBLICATION.md](_workflows/WORKFLOW_PUBLIC_PUBLICATION.md))

## C) Governance and auditability

Keep using override requests and decision logs as the formal exception path rather than bypassing rules ad hoc. This is already one of the strongest design choices in the platform and should remain central as complexity grows. See: [_workflows/WORKFLOW_GOVERNANCE_OVERRIDE.md](_workflows/WORKFLOW_GOVERNANCE_OVERRIDE.md), [_workflows/WORKFLOW_RESULT_PIPELINE.md](_workflows/WORKFLOW_RESULT_PIPELINE.md), [_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md](_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md)

***

# Suggested release framing

## v2 — “Reliable operations”

Focus:

*   state/ownership matrix,
*   blocking policy matrix,
*   finance automation,
*   event-driven notifications,
*   basic progression assistants (see [TECHNICAL_NOTE](TECHNICAL_NOTE.md), [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_FINANCIAL_TRACKING.md](_workflows/WORKFLOW_FINANCIAL_TRACKING.md), [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md)).

## v3 — “Rule-aware federation engine”

Focus:

*   unified eligibility engine,
*   explainable standings and qualification,
*   sanction impact automation,
*   stronger self-service for referees and clubs (see [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md), [_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md](_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md), [_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md](_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md), [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md), [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md)).

## v4 — “Mature federation platform”

Focus:

*   advanced public experience,
*   KPI/reporting maturity,
*   season rollover/historical archive tools,
*   long-term data governance and operational intelligence (see [_workflows/WORKFLOW_PUBLIC_PUBLICATION.md](_workflows/WORKFLOW_PUBLIC_PUBLICATION.md), [_workflows/WORKFLOW_FINANCIAL_TRACKING.md](_workflows/WORKFLOW_FINANCIAL_TRACKING.md), [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_DATA_IMPORT.md](_workflows/WORKFLOW_DATA_IMPORT.md)).

***

# Final recommendation

The project already has a **strong v1 foundation** because the architecture, workflows, and governance model are more mature than most custom Odoo federation projects. The roadmap should therefore avoid random expansion and instead follow this sequence:

1.  **Make current rules and state semantics explicit**. See: [TECHNICAL_NOTE](TECHNICAL_NOTE.md), [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_RESULT_PIPELINE.md](_workflows/WORKFLOW_RESULT_PIPELINE.md)
2.  **Automate the obvious admin-heavy transitions**. See: [_workflows/WORKFLOW_FINANCIAL_TRACKING.md](_workflows/WORKFLOW_FINANCIAL_TRACKING.md), [_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md](_workflows/WORKFLOW_COMPLIANCE_MANAGEMENT.md), [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md)
3.  **Centralize eligibility and competition intelligence**. See: [_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md), [_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md](_workflows/WORKFLOW_DISCIPLINE_PIPELINE.md), [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md)
4.  **Invest in self-service, reporting, and long-term platform maturity**. See: [_workflows/WORKFLOW_SEASON_REGISTRATION.md](_workflows/WORKFLOW_SEASON_REGISTRATION.md), [_workflows/WORKFLOW_PUBLIC_PUBLICATION.md](_workflows/WORKFLOW_PUBLIC_PUBLICATION.md), [_workflows/WORKFLOW_FINANCIAL_TRACKING.md](_workflows/WORKFLOW_FINANCIAL_TRACKING.md), [_workflows/WORKFLOW_DATA_IMPORT.md](_workflows/WORKFLOW_DATA_IMPORT.md)

If you want, I can turn this next into one of these formats:

1.  **A backlog with epics → features → tasks**,
2.  **A quarterly roadmap (Q2/Q3/Q4...)**, or
3.  **A release plan with v2/v3/v4 scope, dependencies, and acceptance criteria**.

The most useful next step would probably be **option 1: backlog with epics and concrete work packages**.
