# Sports Federation Reporting

Cross-module analytical reports backed by PostgreSQL views. Provides read-only
report models that aggregate data from participation, officiating, compliance,
and finance into summary tables.

## Purpose

Gives federation administrators a **dashboard-level view** of key metrics without
writing SQL or building custom reports. Each report model is a database view
that joins and aggregates data from multiple modules into a single, filterable
list or pivot view.

## Dependencies

| Module | Reason |
|--------|--------|
| `sports_federation_base` | Clubs, teams, seasons |
| `sports_federation_people` | Players |
| `sports_federation_tournament` | Tournaments |
| `sports_federation_officiating` | Referees, assignments |
| `sports_federation_standings` | Standings data |
| `sports_federation_discipline` | Disciplinary data |
| `sports_federation_compliance` | Compliance data |
| `sports_federation_finance_bridge` | Finance events |

## Models (all SQL view-backed, `_auto = False`)

### `federation.report.participation`

Club participation summary per season.

| Field | Type | Description |
|-------|------|-------------|
| `season_id` | Many2one | Season |
| `club_id` | Many2one | Club |
| `team_count` | Integer | Teams registered |
| `player_count` | Integer | Players licensed |
| `tournament_count` | Integer | Tournaments entered |

### `federation.report.officiating`

Referee workload summary.

| Field | Type | Description |
|-------|------|-------------|
| `referee_id` | Many2one | Referee |
| `certification_level` | Char | Current level |
| `assignment_count` | Integer | Total assignments |
| `completed_assignment_count` | Integer | Completed assignments |

### `federation.report.compliance`

Compliance status overview by entity type.

| Field | Type | Description |
|-------|------|-------------|
| `target_model` | Char | Entity type |
| `compliant_count` | Integer | Entities in compliance |
| `missing_count` | Integer | Missing documents |
| `pending_count` | Integer | Awaiting review |
| `expired_count` | Integer | Expired documents |

### `federation.report.finance`

Financial event summary by fee type and state.

| Field | Type | Description |
|-------|------|-------------|
| `fee_type_id` | Many2one | Fee category |
| `state` | Selection | Event state |
| `event_count` | Integer | Number of events |
| `total_amount` | Float | Sum of amounts |

## Key Behaviours

1. **Read-only views** — Models use `_auto = False` with `init()` creating SQL views.
2. **Pivot and graph support** — Views are configured for pivot-table and graphical
   analysis.
3. **Cross-module joins** — Each report aggregates from multiple modules' tables.
4. **Zero maintenance** — Reports auto-refresh as underlying data changes.

## CSV exports

Authenticated backend users can export lightweight KPI CSV files from the
reporting controllers:

- `/reporting/export/standings/<tournament_id>` — standings lines with tie-break notes
- `/reporting/export/participation/<season_id>` — season participation roster
- `/reporting/export/finance` — finance summary grouped by fee type and state
