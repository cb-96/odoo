# Workflow: Financial Tracking

Lightweight financial event recording for registration fees, disciplinary fines,
referee reimbursements, and other federation-related financial activity.

## Overview

The federation needs to track money flowing in and out — registration fees from
clubs, fines from disciplinary actions, reimbursements for referees — without
requiring a full accounting module. The finance bridge module records these as
**finance events** linked to their source, with states that prepare them for
future accounting integration.

## Modules Involved

| Module | Role |
|--------|------|
| `sports_federation_finance_bridge` | Fee types, finance events |
| `sports_federation_base` | Clubs (fee payers) |
| `sports_federation_people` | Players (registration fees) |
| `sports_federation_tournament` | Tournament context |
| `sports_federation_officiating` | Referees (reimbursements) |
| `sports_federation_discipline` | Sanctions (fines) |
| `sports_federation_reporting` | Financial summary reports |

## Step-by-Step Flow

### 1. Fee Type Catalogue Setup

**Actor**: Federation administrator
**Module**: `sports_federation_finance_bridge`

1. Navigate to **Federation → Finance → Fee Types**.
2. Create fee type entries:

| Example | Category | Default Amount |
|---------|----------|---------------|
| Season Registration Fee | `registration` | €250.00 |
| Player License Fee | `registration` | €25.00 |
| Disciplinary Fine (Yellow Card) | `fine` | €50.00 |
| Disciplinary Fine (Red Card) | `fine` | €150.00 |
| Referee Travel Reimbursement | `reimbursement` | €75.00 |
| Match Officials Fee | `reimbursement` | €100.00 |
| Venue Booking (passthrough) | `other` | variable |

Each fee type has a unique code, category, and default amount.

### 2. Finance Event Creation

**Actor**: Federation staff or automated from source modules
**Module**: `sports_federation_finance_bridge`

Finance events are created in two ways:

**Manual**: Staff creates an event from the Finance Events list view.

**From source modules**: Other modules create events when relevant actions occur:
- Registration approved → registration fee event
- Sanction with fine → fine event
- Referee assignment completed → reimbursement event
 - Venue confirmed for a match → venue booking event (created manually via the
     **Create Venue Charge** match header button or programmatically via
     `match.action_create_venue_finance_event()`). The default fee type code used
     is `venue_booking` but implementations may map to a different fee type.

Each event records:
- Fee type (from catalogue)
- Amount and currency
- Source record (via `source_model` / `source_res_id`)
- Target entity: club, player, or referee
- Partner (for accounting integration)

### 3. Event Confirmation

**Actor**: Federation finance staff
**Module**: `sports_federation_finance_bridge`

1. Review draft finance events.
2. Verify amounts and source references.
3. **Confirm**: state `draft` → `confirmed`.
4. Confirmed events represent accepted financial obligations.

### 4. Invoicing

**Actor**: Federation finance staff
**Module**: `sports_federation_finance_bridge`

1. For confirmed events that need an external accounting reference:
2. Create or look up the invoice in the accounting system (future integration point).
3. Record the invoice reference in `invoice_ref`.
4. Keep the bridge event in `confirmed` until it is financially settled.

### 5. Payment Recording

**Actor**: Federation finance staff
**Module**: `sports_federation_finance_bridge`

1. When payment is received or reimbursement is completed:
2. Set state to `settled`.
3. Record external references if applicable (`external_ref`).

### 6. Cancellation

**Actor**: Federation administrator
**Module**: `sports_federation_finance_bridge`

1. Events can be cancelled at any stage before `settled`.
2. State → `cancelled`.
3. Cancelled events remain in the system for audit but are excluded from totals.

### 7. Reporting

**Actor**: Federation administrator
**Module**: `sports_federation_reporting`

The **Finance Report** (SQL view-backed model) provides:
- Summary by fee type and state
- Total amounts per category
- Event counts for monitoring
- CSV export via `/reporting/export/finance` for leadership dashboards

## State Diagram

```
Finance Event: draft → confirmed → settled
                     → cancelled (from any pre-settled state)
```

## Financial Event Sources

| Source Action | Fee Category | Auto-Created? |
|--------------|-------------|---------------|
| Season registration approved | Registration | Yes |
| Player license issued | Registration | Extendable |
| Tournament participation | Registration | Extendable |
| Disciplinary fine | Fine | Extendable |
| Referee assignment completed | Reimbursement | Extendable |

> Note: The finance bridge provides the **framework** and now includes default
> hooks for season-registration confirmation and match result approval. Other
> modules can continue to create finance events programmatically via the shared
> finance event API.

## Accounting Integration Points

The module is designed to bridge to a full accounting system:

| Field | Purpose |
|-------|---------|
| `partner_id` | Maps to `res.partner` for accounting |
| `invoice_ref` | Links to accounting invoice |
| `external_ref` | External system reference |
| `currency_id` | Multi-currency support |
| `state` (`confirmed`/`settled`) | Aligns with the current lightweight workflow |

## Related Workflows

- [Season Registration](WORKFLOW_SEASON_REGISTRATION.md) — registration fee generation
- [Discipline Pipeline](WORKFLOW_DISCIPLINE_PIPELINE.md) — fine event generation
- [Match Day Operations](WORKFLOW_MATCH_DAY_OPERATIONS.md) — referee reimbursement events
