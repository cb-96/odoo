# Workflow: Discipline Pipeline

From match incident through investigation, decision, sanctions, and suspensions.

## Overview

When an incident occurs during a match (card, misconduct, violence), it triggers
a formal disciplinary process. Incidents are reported, grouped into cases,
investigated, and resolved with sanctions (fines, warnings) or suspensions
(match bans). The pipeline ensures fair, documented, and auditable handling.

## Modules Involved

| Module | Role |
|--------|------|
| `sports_federation_discipline` | Incidents, cases, sanctions, suspensions |
| `sports_federation_tournament` | Match context where incidents occur |
| `sports_federation_people` | Player subject records |
| `sports_federation_officiating` | Referee as incident reporter |
| `sports_federation_base` | Club subject records |
| `sports_federation_finance_bridge` | Fine amounts as finance events |
| `sports_federation_governance` | Appeals via override requests |
| `mail` | Chatter on discipline records |

## Step-by-Step Flow

### 1. Incident Reporting

**Actor**: Referee, match official, or federation staff
**Module**: `sports_federation_discipline`

1. During or after a match, create a **match incident** record.
2. Fill in:
   - Match reference
   - Player involved
   - Club involved
   - Reporting referee
   - Incident type: `yellow_card`, `red_card`, `misconduct`, `violence`, `other`
   - Match minute and description
3. Incident is created in `reported` status.
4. Date reported and reporting user are recorded automatically.

Incidents are visible on the match form view via inherited tabs.

### 2. Case Creation

**Actor**: Disciplinary staff
**Module**: `sports_federation_discipline`

1. Create a **disciplinary case** to group one or more related incidents.
2. Case receives an automatic reference number via `ir.sequence` (`FED-DISC-XXXXX`).
3. Link incident(s) to the case.
4. Identify the subject: player, club, or referee.
5. Assign a responsible user (case handler).
6. Case opens in `open` state.

### 3. Investigation

**Actor**: Case handler (disciplinary staff)
**Module**: `sports_federation_discipline`

1. Move case to `investigation` state.
2. Gather evidence: review referee reports, match sheets, video footage.
3. Interview parties if needed.
4. Document findings in the case summary and notes fields.
5. Review related incidents for context (prior incidents for same player/club).

### 4. Decision

**Actor**: Disciplinary committee / case handler
**Module**: `sports_federation_discipline`

1. Move case to `decided` state.
2. `decided_on` date is recorded.
3. Create one or more **sanctions** and/or **suspensions** as outcomes.

#### Sanctions

| Type | Description |
|------|-------------|
| `fine` | Monetary penalty (amount + currency) |
| `warning` | Formal written warning |
| `ban` | Competition ban |
| `point_deduction` | Points deducted from standings |
| `other` | Custom sanction |

Each sanction records: type, target (player/club/referee), amount, effective date.

#### Suspensions

A time-bound match ban for a player:
- `date_start` / `date_end` define the ban period.
- States: `active` → `served` → `overturned`.
- Active suspensions are checked during match-sheet validation (player flagged
  as `is_suspended`).

### 5. Financial Recording

**Actor**: Federation administrator
**Module**: `sports_federation_finance_bridge`

1. For sanctions of type `fine`, create a **finance event**.
2. Link to the sanction source via `source_model` / `source_res_id`.
3. Finance event is created automatically and tracks payment: `draft` → `confirmed` → `settled`.

### 6. Case Closure

**Actor**: Disciplinary staff
**Module**: `sports_federation_discipline`

1. Once all sanctions are issued, suspensions are active, and fines are recorded,
   move case to `closed` state.
2. `closed_on` date is recorded.
3. The case becomes a permanent record in the player's/club's discipline history.

### 7. Appeal (Exception Path)

**Actor**: Sanctioned party
**Module**: `sports_federation_governance`

1. If the sanctioned party disputes the decision, file an **override request**.
2. The governance workflow handles review and decision.
3. If the appeal succeeds, the suspension state can be changed to `overturned`
   and sanctions may be revised.

## State Diagram

```
Incident: reported → under_review → resolved
                                   → dismissed

Case: open → investigation → decided → closed

Suspension: active → served
                   → overturned

Sanction: (no state machine — created as final)

Finance Event: draft → confirmed → settled
                                 → cancelled
```

## Integration Points

| Integration | Detail |
|-------------|--------|
| Match form | Incidents tab added to match views |
| Player form | Discipline tab shows player's incident/case history |
| Match sheets | Suspended players flagged (`is_suspended`) |
| Standings | Point deduction sanctions affect standings |
| Finance | Fines create finance events for tracking |

## Related Workflows

- [Match Day Operations](WORKFLOW_MATCH_DAY_OPERATIONS.md) — incident reporting during matches
- [Governance Override](WORKFLOW_GOVERNANCE_OVERRIDE.md) — appeal process
- [Financial Tracking](WORKFLOW_FINANCIAL_TRACKING.md) — fine payment tracking
