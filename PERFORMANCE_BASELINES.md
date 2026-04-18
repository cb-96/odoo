# Performance Baselines

Last updated: 2026-04-18
Owner: Federation Platform Team
Last reviewed: 2026-04-18
Review cadence: Every release

This document records the query-count budgets enforced in CI for the slowest
public, portal, and reporting helpers. The budgets are intentionally small so
N+1 regressions become visible before release, while the SQL plan watchpoints
highlight which operators usually dominate the heavy reporting views.

## Public And Portal Budgets

- `federation.tournament.get_public_featured_tournaments(limit=4)`: `1` query.
- `federation.tournament.get_public_live_tournaments(limit=4)`: `1` query.
- `federation.tournament.get_public_recent_result_tournaments(limit=4)`: `3` queries after batching approved-match lookups and ranking the latest approved match per tournament.
- `federation.tournament.get_public_schedule_sections()`: `4` queries.
- `federation.team.roster.line._portal_get_available_players()`: `7` queries with the current portal ownership and team-scope checks.

## Reporting Budgets

- `federation.report.schedule._build_season_portfolio_rows()`: `3` queries.
- `federation.report.schedule._build_club_performance_rows()`: `4` queries.

## SQL Plan Watchpoints

- `federation_report_season_portfolio`: expect aggregate and sort or window operators because the view rolls up season registrations, finance events, budgets, and compliance checks through multiple CTEs.
- `federation_report_club_performance`: expect aggregate and sort or window operators because the view unions match sides before club-level rollups and season ordering.

## Regression Coverage

- Public-site budgets are asserted in `sports_federation_public_site/tests/test_public_api.py`.
- Portal roster budgets are asserted in `sports_federation_portal/tests/test_roster_portal_access.py`.
- Reporting budgets and plan watchpoints are asserted in `sports_federation_reporting/tests/test_operational_reporting.py`.