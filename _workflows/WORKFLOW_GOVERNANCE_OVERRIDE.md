# Workflow: Governance Override

Formal exception-request process for situations that require bending standard
rules — with structured decision-making and full audit trails.

## Overview

Standard federation processes have rules and constraints (registration deadlines,
eligibility criteria, squad limits). When legitimate exceptions are needed, the
governance module provides a formal **request → review → decide → implement**
pipeline that ensures every exception is justified, documented, and auditable.

## Modules Involved

| Module | Role |
|--------|------|
| `sports_federation_governance` | Override requests, decisions, audit notes |
| `sports_federation_base` | Core entities referenced by requests |
| `sports_federation_people` | Player references |
| `sports_federation_tournament` | Tournament references |
| `mail` | Chatter tracking on requests |

## Common Override Scenarios

| Scenario | Example |
|----------|---------|
| Late registration | Club missed the deadline but has valid reason |
| Eligibility exception | Player doesn't meet age rule but has special dispensation |
| Replayed match | Match result voided and replay ordered |
| Transfer exception | Player transfer outside normal window |
| Sanction reduction | Appeal of disciplinary sanction succeeds |
| Roster override | Squad exceeds maximum due to special circumstances |

## Step-by-Step Flow

### 1. Override Request Creation

**Actor**: Federation official or authorised user
**Module**: `sports_federation_governance`

1. Navigate to **Federation → Governance → Override Requests**.
2. Create a new request:
   - Title describing the exception
   - Request type (categorises the override)
   - Target record (via `target_model` / `target_res_id` — links to any Odoo record)
   - Justification in the `reason` field
3. The requester and request timestamp are recorded automatically.
4. Request starts in `draft` state.

### 2. Request Submission

**Actor**: Requester
**Module**: `sports_federation_governance`

1. Review the draft request for completeness.
2. Submit the request: state → `submitted`.
3. Governance officers are notified (via chatter or activity).

### 3. Review Process

**Actor**: Governance officer(s)
**Module**: `sports_federation_governance`

1. A governance officer picks up the request: state → `under_review`.
2. Officer reviews the justification, target record, and context.
3. May add **audit notes** documenting questions, findings, or follow-ups.
4. May request additional information from the requester.

### 4. Decision

**Actor**: Governance officer(s)
**Module**: `sports_federation_governance`

1. Create an **override decision** on the request.
2. Decision options:
   - `approve` — Exception is granted
   - `reject` — Exception is denied
   - `request_info` — More information needed
3. Decision records: decision maker, timestamp, and reasoning.
4. Multiple decisions are supported (e.g. committee voting).

Based on the decision(s):
- If approved: request state → `approved`
- If rejected: request state → `rejected`

### 5. Implementation

**Actor**: Federation administrator
**Module**: `sports_federation_governance` + relevant module

1. If approved, the administrator implements the exception in the relevant module
   (e.g. creates a late registration, overrides an eligibility check).
2. Documents the implementation in the `implementation_note` field.
3. Request state → `implemented`.

### 6. Audit Trail

**Actor**: System (automatic)
**Module**: `sports_federation_governance`

The complete audit trail includes:
- Request creation with requester and timestamp
- Every decision with decision maker, timestamp, and reasoning
- Audit notes with author and timestamp
- Implementation notes
- Chatter log of all state changes

## State Diagram

```
Override Request: draft → submitted → under_review → approved → implemented
                                                   → rejected

Decision: approve / reject / request_info
          (attached to request as child records)
```

## Security Model

| Group | Permissions |
|-------|-------------|
| Federation Staff | Can create override requests |
| Governance Officer | Can review, decide, and manage requests |

## Generic Target

Override requests use a **model/res_id pattern** that can link to any record type:
- `federation.season.registration` — late registration override
- `federation.player` — eligibility exception
- `federation.match` — replayed match decision
- `federation.sanction` — sanction reduction
- `federation.team.roster` — roster limit exception

This makes the governance module universally applicable without hard dependencies
on specific modules.

## Related Workflows

- [Result Pipeline](WORKFLOW_RESULT_PIPELINE.md) — contested results may trigger overrides
- [Discipline Pipeline](WORKFLOW_DISCIPLINE_PIPELINE.md) — sanction appeals
- [Season Registration](WORKFLOW_SEASON_REGISTRATION.md) — late registration exceptions
- [Compliance Management](WORKFLOW_COMPLIANCE_MANAGEMENT.md) — compliance exceptions
