# Workflow: Result Pipeline

Score submission through verification, approval, and standings integration.
Ensures match results are reviewed before becoming official.

## Overview

After a match is played and scores are entered, the result must pass through a
formal review pipeline before it counts toward official standings. This prevents
data-entry errors and disputed scores from corrupting competition tables.

## Modules Involved

| Module | Role |
|--------|------|
| `sports_federation_result_control` | Result state machine, verification, approval |
| `sports_federation_tournament` | Match model (base for result fields) |
| `sports_federation_standings` | Standings computation using approved results |
| `sports_federation_governance` | Override requests for disputed results |
| `sports_federation_public_site` | Publishing approved results publicly |
| `mail` | Chatter audit trail on matches |

## Step-by-Step Flow

### 1. Score Entry

**Actor**: Federation staff or match official
**Module**: `sports_federation_tournament`

1. Open the match record after the game concludes.
2. Enter `home_score` and `away_score`.
3. Set match state to `completed`.

At this point the result is entered but **not yet official**.

### 2. Result Submission

**Actor**: Federation staff
**Module**: `sports_federation_result_control`

1. Click **Submit Result** on the match form.
2. `result_state` transitions from `not_submitted` → `submitted`.
3. `result_submitted_by_id` and `result_submitted_on` are recorded automatically.
4. The result is now in the verification queue.

### 3. Result Verification

**Actor**: Result Verifier (security group)
**Module**: `sports_federation_result_control`

1. Verifier reviews the submitted result.
2. Cross-checks against match sheet records, referee reports, and incident logs.
3. Click **Verify Result**.
4. `result_state` transitions from `submitted` → `verified`.
5. `result_verified_by_id` and `result_verified_on` are recorded.

### 4. Result Approval

**Actor**: Result Approver (security group)
**Module**: `sports_federation_result_control`

1. Approver reviews the verified result.
2. Click **Approve Result**.
3. `result_state` transitions from `verified` → `approved`.
4. `result_approved_by_id` and `result_approved_on` are recorded.
5. `include_in_official_standings` is set to `True`.

The result is now **official** and eligible for standings computation.

### 5. Contest (Exception Path)

**Actor**: Club representative or federation official
**Module**: `sports_federation_result_control`

1. If a party disputes the result, click **Contest Result**.
2. `result_state` transitions to `contested`.
3. `result_contest_reason` is filled in with the dispute justification.
4. The result is excluded from standings until resolved.

### 6. Correction (Exception Path)

**Actor**: Federation administrator
**Module**: `sports_federation_result_control`, `sports_federation_governance`

1. After review of the contest, the result may be corrected.
2. Update scores if needed.
3. Click **Correct Result**.
4. `result_state` transitions to `corrected`.
5. `result_correction_reason` is recorded.
6. A governance override request may be filed for audit purposes.
7. The corrected result can be re-submitted through the pipeline.

### 7. Standings Update

**Actor**: Federation administrator
**Module**: `sports_federation_standings`

1. Open the relevant standings record (tournament, stage, or group level).
2. **Recompute standings** — only results with `include_in_official_standings = True`
   are included.
3. Points are calculated using the rule set (win/draw/loss values).
4. Tie-break rules are applied in sequence order.
5. Standings states: `draft` → `computed` → `published`.

### 8. Publication

**Actor**: Federation administrator
**Module**: `sports_federation_public_site`

1. Publish the standings record (`website_published = True`).
2. If the tournament has `show_public_results = True`, individual match results
   appear on the public competition page.
3. Public pages update to reflect the latest approved data.

## State Diagram

```
Result: not_submitted → submitted → verified → approved
                                              → contested → corrected
                                                          → (re-submit)

Standings: draft → computed → published
```

## Security Model

| Group | Permissions |
|-------|-------------|
| Federation Staff | Submit results |
| Result Verifier | Verify submitted results |
| Result Approver | Approve verified results |

Each step requires a different security group, enforcing **separation of duties**.

## Audit Trail

Every state transition is recorded with:
- **Who**: user ID of the person performing the action
- **When**: datetime timestamp
- **What**: Odoo chatter log entry on the match record

## Related Workflows

- [Match Day Operations](WORKFLOW_MATCH_DAY_OPERATIONS.md) — score entry context
- [Tournament Lifecycle](WORKFLOW_TOURNAMENT_LIFECYCLE.md) — standings in tournament context
- [Governance Override](WORKFLOW_GOVERNANCE_OVERRIDE.md) — contested result escalation
