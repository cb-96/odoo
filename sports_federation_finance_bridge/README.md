# Sports Federation Finance Bridge

Records billable and reimbursable federation events without requiring a full
accounting module. Provides fee types and finance events as a lightweight
financial tracking layer.

## Purpose

Bridges the gap between federation operations and future accounting integration.
Every registration fee, disciplinary fine, or referee reimbursement is logged as a
**finance event** with amount, state, and source reference — ready to be fed into
an accounting system when one is connected.

## Dependencies

| Module | Reason |
|--------|--------|
| `sports_federation_base` | Clubs |
| `sports_federation_people` | Players |
| `sports_federation_tournament` | Tournament context |
| `sports_federation_result_control` | Result approval pipeline (automatic event hooks) |
| `sports_federation_officiating` | Referees |
| `sports_federation_discipline` | Fines and sanctions |

## Models

### `federation.fee.type`

A catalogue of fee categories.

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Fee type name |
| `code` | Char | Unique code |
| `category` | Selection | registration / fine / reimbursement / other |
| `default_amount` / `currency_id` | Monetary | Default amount |
| `active` | Boolean | In use |
| `notes` | Text | Description |

### `federation.finance.event`

An individual financial occurrence.

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Event title |
| `fee_type_id` | Many2one | Fee category |
| `event_type` | Selection | Type classification |
| `amount` / `currency_id` | Monetary | Actual amount |
| `state` | Selection | draft / confirmed / settled / cancelled |
| `source_model` / `source_res_id` | Char / Integer | Origin record |
| `partner_id` | Many2one | Related partner |
| `club_id` / `player_id` / `referee_id` | Many2one | Federation entity |
| `invoice_ref` / `external_ref` | Char | External references |
| `notes` | Text | Details |

- **State machine**: draft → confirmed → settled / cancelled.

## Key Behaviours

1. **Source traceability** — Every finance event links back to its originating record
   (registration, sanction, assignment) via model/res_id.
2. **Fee catalogue** — Standardised fee types with default amounts.
3. **Accounting-ready** — `invoice_ref` and `external_ref` keep the bridge ready
   for future accounting integration while the current lightweight workflow ends
   in `settled`.
4. **Multi-entity** — Covers clubs, players, and referees.

## Season Registration Finance Hooks

The finance bridge now auto-creates a finance event when a
`federation.season.registration` record moves into `confirmed`.

- Default fee type code: `season_registration`
- Creation mode: idempotent; reconfirming a registration reuses the same source
  record and does not create duplicates
- Source traceability: events use `source_model = federation.season.registration`
  and `source_res_id = <registration id>`

## Result Approval Finance Hooks (Phase 2)

match_result_hooks.py extends `federation.match` with:

- **`result_fee_type_id`** (Many2one → `federation.fee.type`): optional; when set,
  a `federation.finance.event` (charge) is automatically created when
  `action_approve_result()` completes.
- **`result_finance_event_ids`** (computed): all finance events whose source is
  this match record.
- **`action_approve_result()`** override: calls the base result pipeline and then
  fires the auto-event.

### Migration note (v19.0.1.1.0)

A new field `result_fee_type_id` (Many2one, nullable) is added to
`federation.match`.  Run `-u sports_federation_finance_bridge` after upgrade.