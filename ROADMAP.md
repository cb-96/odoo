# ROADMAP — Multi-Year Product and Engineering Plan

Last updated: 2026-04-10

This roadmap replaces the short tactical plan with a multi-year view organized
around the module boundaries already present in the repository. The goal is to
move from a strong technical base to a release-ready federation platform, then
to a more automated, self-service, and analytics-driven operating model.

## Planning Principles

- Close end-to-end workflows before adding feature breadth.
- Keep module boundaries intact and push reusable logic into services and
  wizards rather than cross-module shortcuts.
- Treat tests, security, documentation, and migration notes as part of feature
  completion.
- Prioritize federation-critical flows first: registration, eligibility,
  scheduling, match-day execution, results, standings, finance, and publication.
- Keep mail, OAuth, and external integrations env-driven and reproducible in CI.

## Module Groups

Core competition platform:
`sports_federation_base`, `sports_federation_tournament`,
`sports_federation_competition_engine`, `sports_federation_result_control`,
`sports_federation_standings`

Participant and operations modules:
`sports_federation_people`, `sports_federation_rosters`,
`sports_federation_officiating`, `sports_federation_venues`,
`sports_federation_rules`

Oversight and control modules:
`sports_federation_discipline`, `sports_federation_governance`,
`sports_federation_compliance`

Delivery surfaces and supporting utilities:
`sports_federation_portal`, `sports_federation_public_site`,
`sports_federation_notifications`, `sports_federation_reporting`,
`sports_federation_import_tools`, `sports_federation_finance_bridge`

## Multi-Year Plan Overview

| Year | Theme | Primary Outcome | Main Module Focus |
| --- | --- | --- | --- |
| Year 1 | Release readiness and workflow closure | Stable, testable, secure federation core ready for pilot or first production rollout | Base, tournament, competition engine, people, rosters, result control, standings, portal, public site, venues, finance bridge, notifications, reporting |
| Year 2 | Operational depth and federation controls | Policy-heavy modules become first-class operational tools | Discipline, governance, compliance, finance bridge, officiating, reporting, notifications, import tools |
| Year 3 | Self-service and ecosystem expansion | Clubs and federation staff operate more through portal/public workflows and external integrations | Portal, public site, notifications, import tools, reporting, finance bridge |
| Year 4 | Intelligence, planning, and scale | Federation-wide analytics, stronger reconciliation, and outward-facing interfaces | Reporting, compliance, governance, finance bridge, base, import tools |

## Year 1 Goal

Year 1 is about making the suite dependable enough for real operational use.
That means finishing the core federation lifecycle, reducing manual workarounds,
hardening security, and ensuring every critical flow is supported by tests,
documentation, and operator-safe UI or wizard behavior.

## Year 1 Detailed Breakdown By Priority

### Priority 0 — Must-Have Foundation and Release Blockers

1. Done (2026-04-10): Stabilize canonical master data and state models.
Modules: `sports_federation_base`, `sports_federation_people`, `sports_federation_tournament`, `sports_federation_portal`.
Work: review all core records for mandatory fields, sequences, archive behavior, ownership fields, and state transitions; align technical notes, workflows, and tests with the actual ORM implementation.
Done when: core records used in season registration and competition operations have clear lifecycle coverage, explicit ACLs, and focused tests.

2. Done (2026-04-10): Close the season registration flow end to end.
Modules: `sports_federation_base`, `sports_federation_people`, `sports_federation_portal`, `sports_federation_finance_bridge`, `sports_federation_notifications`.
Work: move a club from draft registration through portal submission, validation, confirmation, finance-event creation, and notification logging without manual bridging steps.
Done when: one reproducible flow covers draft to confirmed registration with side effects that are idempotent and tested.

3. Done (2026-04-10): Make competition setup deterministic and operator-safe.
Modules: `sports_federation_tournament`, `sports_federation_competition_engine`, `sports_federation_rules`, `sports_federation_venues`.
Work: harden tournament templates, stage/group setup, round-robin generation, knockout bracket generation, gameday assignment, and stage progression; ensure preview-first behavior and overwrite safeguards in wizards.
Done when: administrators can generate schedules repeatedly with deterministic outputs and no destructive surprises.

4. Done (2026-04-10): Lock down result integrity and standings correctness.
Modules: `sports_federation_result_control`, `sports_federation_standings`, `sports_federation_rules`.
Work: enforce submit, verify, approve separation of duties; ensure contested and corrected results behave correctly; keep official standings limited to approved outcomes; preserve tie-break explanation visibility.
Done when: official standings can be defended operationally and every exception path has regression coverage.

5. Harden portal and public-site security before wider rollout.
Modules: `sports_federation_portal`, `sports_federation_public_site`.
Work: verify ownership checks on portal writes, validate all public visibility flags, avoid unsafe template rendering, and cover direct-URL access paths with controller tests.
Done when: public and portal surfaces enforce the same data-ownership and publication rules described in the workflows.

6. Standardize CI, secrets handling, and contributor setup.
Modules: repository-wide, with emphasis on `ci/`, `sports_federation_public_site`, `sports_federation_portal`, `sports_federation_standings`, `sports_federation_venues`, `sports_federation_finance_bridge`, `sports_federation_reporting`.
Work: keep CI env-driven, expand targeted module tests, validate scripts, and document local execution for maintainers.
Done when: contributors can run focused tests locally and GitHub Actions can validate critical flows without committed secrets.

7. Bring repository documentation up to release quality.
Modules: repository docs plus every module touched by critical workflow work.
Work: keep `TECHNICAL_NOTE.md`, `CONTEXT.md`, workflow documents, module READMEs, integration docs, and state/ownership references aligned with the implemented code.
Done when: a new maintainer can understand the main system flows without relying on tribal knowledge.

### Priority 1 — High-Value Operational Completeness

1. Apply eligibility and license rules in real workflows.
Modules: `sports_federation_people`, `sports_federation_rules`, `sports_federation_rosters`, `sports_federation_portal`, `sports_federation_tournament`.
Work: connect eligibility checks to participant confirmation, roster validation, and match-sheet readiness; present operator-readable failure reasons instead of opaque blocks.
Done when: ineligible players are blocked consistently before official competition actions.

2. Complete roster and match-sheet operations.
Modules: `sports_federation_rosters`, `sports_federation_people`, `sports_federation_portal`, `sports_federation_result_control`.
Work: support season rosters, match-day roster locking, substitutions governance, and audit history tied to results and disputes.
Done when: match-day participation is traceable and synchronized with eligibility and discipline status.

3. Complete officiating assignment and confirmation workflows.
Modules: `sports_federation_officiating`, `sports_federation_tournament`, `sports_federation_venues`, `sports_federation_notifications`.
Work: add assignment statuses, confirmation deadlines, shortage alerts, and readiness checks for required official roles.
Done when: operationally ready matches can be identified automatically and missing-official cases create visible exceptions.

4. Expand finance automation from events to process support.
Modules: `sports_federation_finance_bridge`, `sports_federation_base`, `sports_federation_tournament`, `sports_federation_discipline`, `sports_federation_venues`, `sports_federation_reporting`.
Work: extend hooks for reimbursements, discipline-related charges, venue settlements, and reconciliation-friendly references.
Done when: most federation-triggered monetary events are created automatically, remain idempotent, and are exportable.

5. Activate the modeled notification scenarios.
Modules: `sports_federation_notifications`, `sports_federation_portal`, `sports_federation_public_site`, `sports_federation_result_control`, `sports_federation_standings`, `sports_federation_finance_bridge`.
Work: replace notification stubs with actual templates or activities for registration, publication, referee assignment, approved results, standings freeze, and finance confirmations.
Done when: high-value workflow events reliably produce a logged communication or task.

6. Expand reporting from CSV extraction to operational reporting.
Modules: `sports_federation_reporting`, `sports_federation_standings`, `sports_federation_finance_bridge`, `sports_federation_tournament`, `sports_federation_compliance`.
Work: provide federation-facing KPI outputs, reconciliation views, and role-oriented reports that do not require direct database access.
Done when: administrators can produce recurring weekly or monthly operational views from the application layer.

7. Make imports safe enough for onboarding and seasonal rollover.
Modules: `sports_federation_import_tools`, `sports_federation_base`, `sports_federation_people`, `sports_federation_tournament`.
Work: add dry-run validation, duplicate detection, failure reporting, and mapping guidance for initial club, team, player, and season data imports.
Done when: federation onboarding and annual data refreshes can be rehearsed with predictable outcomes.

### Priority 2 — Control, Oversight, and Policy Execution

1. Complete the discipline pipeline and connect it to operations.
Modules: `sports_federation_discipline`, `sports_federation_result_control`, `sports_federation_people`, `sports_federation_rosters`, `sports_federation_standings`.
Work: turn recorded incidents into sanctions, suspensions, and downstream eligibility effects that are visible in roster and match validation.
Done when: discipline outcomes automatically affect player availability and remain auditable.

2. Build compliance operations around real federation obligations.
Modules: `sports_federation_compliance`, `sports_federation_people`, `sports_federation_governance`, `sports_federation_portal`, `sports_federation_reporting`.
Work: track required documents, expiries, remediation tasks, and escalation states for clubs, officials, and staff.
Done when: overdue compliance items appear in actionable queues and reporting outputs.

3. Formalize governance and override controls.
Modules: `sports_federation_governance`, `sports_federation_standings`, `sports_federation_result_control`, `sports_federation_compliance`.
Work: capture approval trails for exceptional decisions, appeals, competition overrides, and federation directives.
Done when: extraordinary decisions are role-gated, auditable, and visible in reporting.

4. Add cross-module reconciliation and audit support.
Modules: `sports_federation_reporting`, `sports_federation_finance_bridge`, `sports_federation_notifications`, `sports_federation_governance`, `sports_federation_compliance`.
Work: build exception reporting for failed notifications, missing finance events, stalled approvals, and inconsistent workflow states.
Done when: federation operators can detect broken processes before end users report them.

### Priority 3 — Strategic Stretch Work If Capacity Remains

1. Deepen public competition storytelling and discoverability.
Modules: `sports_federation_public_site`, `sports_federation_reporting`, `sports_federation_standings`, `sports_federation_tournament`.
Work: improve competition pages, bracket views, fixture presentation, standings explanations, and publication cadence.
Done when: public pages reduce ad hoc communication load on federation staff.

2. Add federation-admin productivity tooling.
Modules: `sports_federation_portal`, `sports_federation_import_tools`, `sports_federation_notifications`, `sports_federation_reporting`.
Work: add saved filters, bulk actions, seasonal checklists, and operational queues for high-volume administrative work.
Done when: recurring seasonal administration takes fewer manual steps and fewer side-channel spreadsheets.

3. Prototype outward-facing integration contracts.
Modules: `sports_federation_reporting`, `sports_federation_finance_bridge`, `sports_federation_notifications`, `sports_federation_import_tools`.
Work: define stable export contracts or lightweight APIs for accounting systems, federation partners, and public data feeds.
Done when: external integrations can be introduced without bypassing the module architecture.

## Year 1 Sequencing Guidance

The intended order inside Year 1 is simple: finish Priority 0 before moving
seriously into Priority 1, use Priority 2 only once the operational core is
stable, and reserve Priority 3 for spare capacity or external pressure. In
practice, that means the first half of the year should be dominated by workflow
closure and hardening, while the second half should emphasize operational depth,
oversight, and selective public experience improvements.

## Year 2 Overview — Operational Depth and Federation Control

Year 2 should move the suite from "works for the core competition lifecycle" to
"operates the federation more broadly." The focus should be on making
discipline, compliance, and governance first-class operational modules,
completing finance process support, deepening officiating operations, and making
reporting useful for management and audit.

Target outcome: federation staff can run policy-heavy operations inside the
platform rather than through email, spreadsheets, and ad hoc decisions.

## Year 3 Overview — Self-Service and Ecosystem Expansion

Year 3 should expand self-service for clubs and external visibility for the
public. The portal should become the preferred interface for club-facing
processes, the public site should present richer competition data safely, and
external integrations should become stable enough for broader ecosystem use.

Target outcome: fewer manual interventions by federation staff and cleaner data
exchange with external systems and stakeholders.

## Year 4 Overview — Intelligence, Planning, and Scale

Year 4 should focus on federation-wide planning and operational intelligence.
Reporting should evolve from exports into decision support, compliance and
governance should produce audit-grade traces, and cross-season analysis should
support strategic planning, budgeting, and performance monitoring.

Target outcome: the platform becomes not just a workflow system, but a planning
and insight system for the federation.

## Ongoing Quality Gates For Every Year

1. Every workflow change must come with tests.
2. Every new model or field change must come with ACL and manifest review.
3. Every behavior change must update the relevant workflow or README.
4. Every integration change must remain env-driven and CI-safe.
5. Every release candidate must include migration notes and rollback guidance.
