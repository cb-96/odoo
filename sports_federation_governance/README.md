# Sports Federation Governance

Formal override-request workflow with decisions and audit trails. Provides a
structured way for federation officials to request, review, and implement
exceptions to standard processes.

## Purpose

Some situations require bending the rules — late registrations, replayed matches,
exceptional eligibility grants. This module ensures those exceptions are
**requested, decided, logged, and auditable** rather than happening informally.

## Dependencies

| Module | Reason |
|--------|--------|
| `sports_federation_base` | Core entities |
| `sports_federation_people` | Player references |
| `sports_federation_tournament` | Tournament references |
| `mail` | Chatter |

## Models

### `federation.override.request`

A formal request to override a standard process.

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Request title |
| `request_type` | Selection | Type of override |
| `target_model` / `target_res_id` | Char / Integer | Linked record |
| `requested_by_id` | Many2one | Requester (user) |
| `requested_on` | Datetime | Request timestamp |
| `state` | Selection | draft / submitted / under_review / approved / rejected / implemented |
| `reason` | Text | Justification |
| `implementation_note` | Text | How it was applied |
| `decision_ids` | One2many | Review decisions |
| `audit_note_ids` | One2many | Audit trail entries |

- **State machine**: draft → submitted → under_review → approved / rejected → implemented.

### `federation.override.decision`

A review decision on an override request.

| Field | Type | Description |
|-------|------|-------------|
| `request_id` | Many2one | The request |
| `decision` | Selection | approve / reject / request_info |
| `decided_by_id` | Many2one | Decision maker |
| `decided_on` | Datetime | Decision timestamp |
| `note` | Text | Reasoning |

### `federation.audit.note`

Free-form audit notes attached to an override request.

| Field | Type | Description |
|-------|------|-------------|
| `request_id` | Many2one | The request |
| `note` | Text | Audit remark |
| `author_id` | Many2one | Author |
| `created_on` | Datetime | Timestamp |

## Security Groups

| Group | Purpose |
|-------|---------|
| Governance Officer | Can review and decide on override requests |

## Key Behaviours

1. **Formal request lifecycle** — Every exception starts as a draft request and
   follows a structured approval flow.
2. **Multi-decision support** — Multiple governance officers can weigh in on a
   single request.
3. **Audit trail** — All decisions and notes are timestamped and attributed.
4. **Generic target** — Requests can link to any record type via model/res_id.
