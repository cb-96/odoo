# CI Tour Roadmap

> **Purpose**: Track all planned and completed Python integration "tour" tests.
> A tour is a single deterministic `TransactionCase` test method (or class) that
> walks a complete real-world workflow from start to finish, verifying every
> state transition and key invariant along the way.
>
> **Convention**:
> - One file per workflow domain, named `test_tour_<domain>.py`
> - Lives in the `tests/` folder of the most relevant module
> - Registered in that module's `tests/__init__.py`
> - Assigned to a CI suite in `ci/run_tests.sh`

---

## Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Implemented and passing |
| 🔄 | In progress |
| 📋 | Planned — spec complete |
| 💡 | Proposed — needs scoping |

---

## Implemented Tours

### ✅ T-01: Full Tournament Lifecycle (RR → Knockout)

- **File**: `sports_federation_competition_engine/tests/test_tournament_tour.py`
- **Class**: `TestTournamentTour`
- **Suite**: `competition_core`
- **Workflow**: `WORKFLOW_TOURNAMENT_LIFECYCLE.md`
- **Tests**:
  - `test_full_tournament_tour_9_teams` — 9-team RR → KO with standings, progression, champion
  - `test_participant_withdrawal_reduces_schedule_scope` — withdraw before schedule, confirm exclusion
  - `test_knockout_only_tournament` — 8-team straight KO bracket, no group stage

---

## Planned Tours

### 📋 T-02: Result Pipeline — Submit / Verify / Approve / Contest / Correct

- **File**: `sports_federation_result_control/tests/test_tour_result_pipeline.py`
- **Suite**: `competition_core`
- **Workflow**: `WORKFLOW_RESULT_PIPELINE.md`
- **Difficulty**: Medium
- **Dependencies**: `sports_federation_result_control`, 3 distinct res.users (submitter, validator, approver)

**Steps**:
1. Create minimal tournament (2 teams, 1 KO match), play match to `done`
2. Submit result → `result_state = "submitted"` (user A)
3. Verify result → `result_state = "verified"` (user B, different from A)
4. Approve result → `result_state = "approved"`, `include_in_official_standings = True` (user C)
5. Assert standing is auto-recomputed with the approved result
6. Contest the approved result with a reason → `result_state = "contested"`, removed from standings
7. Correct the score → `result_state = "corrected"`
8. Re-submit and re-approve (full cycle) → standings recomputed with corrected score

**Key invariants**:
- Same user cannot submit + verify, or verify + approve
- Contested result is removed from standings immediately
- Audit trail has one entry per transition

**Setup note**: Use `self.env.ref('sports_federation_result_control.group_result_validator')`
and `group_result_approver`; create 3 internal users and add to groups in `setUpClass`.

---

### 📋 T-03: Match Day Operations — Roster + Sheet + Referees + Result

- **File**: `sports_federation_officiating/tests/test_tour_match_day.py`
- **Suite**: `people_rosters_rules`
- **Workflow**: `WORKFLOW_MATCH_DAY_OPERATIONS.md`
- **Difficulty**: Hard
- **Dependencies**: `sports_federation_rosters`, `sports_federation_officiating`, `sports_federation_result_control`

**Steps**:
1. Create season, club, team, 12 players on a roster
2. Activate the roster (eligibility pre-check passes)
3. Create a match (scheduled)
4. Create referee (with active certification), assign to match (head referee role)
5. Referee confirms assignment → `assignment.state = "confirmed"`
6. Generate match sheet from the active roster
7. Submit match sheet → `sheet.state = "submitted"`
8. Approve match sheet → `sheet.state = "approved"`
9. Complete the match (score + `action_done`)
10. Lock the match sheet → `sheet.state = "locked"`
11. Mark referee assignment done → `assignment.state = "done"`
12. Submit result for the match

**Key invariants**:
- Ineligible player (suspended or unlicensed) cannot appear on approved sheet
- Assignment cannot be confirmed without a valid (non-expired) certification
- Sheet cannot be locked until match is done

---

### 📋 T-04: Roster Management — Activation, Eligibility Blocks, Mid-Season Change

- **File**: `sports_federation_rosters/tests/test_tour_roster_lifecycle.py`
- **Suite**: `people_rosters_rules`
- **Workflow**: `WORKFLOW_ROSTER_MANAGEMENT.md`
- **Difficulty**: Medium
- **Dependencies**: `sports_federation_rosters`, `sports_federation_people`

**Steps**:
1. Create club, team, 10+ players (all with active licenses)
2. Create a draft roster for a season
3. Attempt to activate with too few players → `ValidationError`
4. Add enough players, activate → `status = "active"`
5. Attempt to create a second active roster for the same scope → `ValidationError`
6. Mid-season: revert to draft, swap a player, re-activate
7. Create a match sheet linked to the active roster
8. Verify suspended player cannot be included on the sheet
9. Close the roster at season end → `status = "closed"`

**Key invariants**:
- One active roster per (team, season, competition) scope (DB unique index)
- Deactivate → re-activate cycle works correctly
- Match sheet respects suspension state at time of generation

---

### 📋 T-05: Season Registration — Club Self-Service to Confirmation

- **File**: `sports_federation_base/tests/test_tour_season_registration.py`
- **Suite**: `competition_core`
- **Workflow**: `WORKFLOW_SEASON_REGISTRATION.md`
- **Difficulty**: Medium
- **Dependencies**: `sports_federation_base`, `sports_federation_portal`

**Steps**:
1. Create a season (draft → open)
2. Create a club with a portal representative user
3. Club submits a registration for the season (portal flow)
4. Admin reviews and confirms the registration
5. Create team linked to the club; enrol in the competition edition
6. Issue player licenses (draft → active)
7. Assert compliance documents are requested
8. Record registration fee finance event (draft → confirmed)
9. Close season → assert registrations and licenses transition correctly

**Key invariants**:
- Portal user can only see their own club's registration
- Duplicate registrations (same club + season) are rejected
- Confirmed registration is required before team enrolment

---

### 📋 T-06: Officiating — Assignment Lifecycle and Shortage Detection

- **File**: `sports_federation_officiating/tests/test_tour_officiating.py`
- **Suite**: `people_rosters_rules`
- **Workflow**: `WORKFLOW_OFFICIATING.md`
- **Difficulty**: Medium
- **Dependencies**: `sports_federation_officiating`

**Steps**:
1. Create 3 referees with active certifications (different levels)
2. Schedule a match 5 days in the future
3. Assign head referee, 2 assistants to the match
4. Confirm each assignment within the 48-hour window
5. Assert all assignments reach `state = "confirmed"`
6. Mark match done, mark all assignments done
7. Create a second match with expired certification referee → assignment check should warn/block
8. Simulate overdue detection scan → missing assignments flagged

**Key invariants**:
- Assignment confirmation deadline = match datetime − 48h
- Referee with expired certification cannot be confirmed
- Shortage (< required officials) detected by scan

---

### 📋 T-07: Discipline — Incident to Case to Sanction to Suspension

- **File**: `sports_federation_discipline/tests/test_tour_discipline_pipeline.py`
- **Suite**: `people_rosters_rules`
- **Workflow**: `WORKFLOW_DISCIPLINE_PIPELINE.md`
- **Difficulty**: Medium
- **Dependencies**: `sports_federation_discipline`

**Steps**:
1. Record an incident on a match (type: red card / unsporting conduct)
2. Create a discipline case linked to the incident (`state = "draft"`)
3. Submit case for review → `state = "under_review"`
4. Reopen to draft to add notes → `state = "draft"` then back to `"under_review"`
5. Issue decision: 2-match suspension + fine
6. Create suspension record → `state = "active"`
7. Create finance event for the fine → `state = "draft"` → `"confirmed"`
8. Close the case → incident auto-closes, suspension remains active
9. Assert the suspended player is flagged ineligible for the next match

**Key invariants**:
- Case can only be reopened from `under_review` → `draft`
- Closure allowed only from `implemented` or `rejected`
- Fine triggers a finance event with the correct category

---

### 📋 T-08: Finance Events — Lifecycle and Auto-Creation Triggers

- **File**: `sports_federation_finance_bridge/tests/test_tour_finance_lifecycle.py`
- **Suite**: `finance_reporting`
- **Workflow**: `WORKFLOW_FINANCIAL_TRACKING.md`
- **Difficulty**: Easy
- **Dependencies**: `sports_federation_finance_bridge`

**Steps**:
1. Create fee type catalogue entries (registration, fine, venue, reimbursement)
2. Manually create a registration finance event → `draft`
3. Confirm the event → `state = "confirmed"`
4. Record payment → `state = "settled"`
5. Create a second event and cancel it → `state = "cancelled"`
6. Trigger an automatic finance event via a confirmed discipline fine
7. Assert `external_ref` deduplication: creating the same event twice is idempotent
8. Export finance events to CSV/report, assert column completeness

**Key invariants**:
- Confirmed events are immutable (amounts/participants cannot change)
- Cancelled events cannot be settled
- Duplicate external_ref is silently skipped (idempotent creation)

---

### 📋 T-09: Public Site — Tournament Publication and Editorial Scheduling

- **File**: `sports_federation_public_site/tests/test_tour_publication.py`
- **Suite**: `release_surfaces`
- **Workflow**: `WORKFLOW_PUBLIC_PUBLICATION.md`
- **Difficulty**: Easy–Medium
- **Dependencies**: `sports_federation_public_site`

**Steps**:
1. Create a tournament with standings and results
2. Set `website_published = True` on the tournament
3. Assert public URL is accessible (controller-level check via `self.url_open`)
4. Set `website_published = True` on the standing → appears in public feed
5. Create an editorial item (`state = "draft"`)
6. Schedule it (set `publish_start`) → `state = "scheduled"`
7. Activate publication → `state = "published"`, visible to unauthenticated requests
8. Archive it → `state = "archived"`, removed from feed
9. Close tournament → assert public pages reflect closed state

**Key invariants**:
- Unpublished tournaments are not visible to portal/public users
- Editorial items outside their `publish_start`/`publish_end` window are hidden
- Approved results only appear on public pages

---

### 📋 T-10: Compliance — Document Submission, Expiry, and Compliance Check

- **File**: `sports_federation_compliance/tests/test_tour_compliance.py`
- **Suite**: `people_rosters_rules`
- **Workflow**: `WORKFLOW_COMPLIANCE_MANAGEMENT.md`
- **Difficulty**: Medium
- **Dependencies**: `sports_federation_compliance`

**Steps**:
1. Define requirements for club entities (e.g., insurance, registration doc)
2. Club submits document → `submission.state = "submitted"`
3. Admin approves → `state = "approved"`
4. Run compliance check → entity is `compliant`
5. Advance date past expiry → submission auto-flagged as `expired`
6. Run compliance check again → entity is `non_compliant`
7. Club re-submits → `state = "submitted"`, approval → `"approved"` (new expiry)
8. Assert renewal reminder notification is created during expiry scan

**Key invariants**:
- Expired submission flips entity to non-compliant immediately
- Re-submission creates a new submission record (no mutation of old ones)
- Compliance check result is point-in-time, not persisted permanently

---

### 📋 T-11: Governance Override — Late Registration Exception

- **File**: `sports_federation_governance/tests/test_tour_governance_override.py`
- **Suite**: `ops_and_notifications`
- **Workflow**: `WORKFLOW_GOVERNANCE_OVERRIDE.md`
- **Difficulty**: Easy
- **Dependencies**: `sports_federation_governance`

**Steps**:
1. Create an override request (type: late registration, linked to a tournament participant)
2. Submit → `state = "submitted"`
3. Withdraw back to draft → `state = "draft"`
4. Resubmit → `state = "submitted"`
5. Governance board approves → `state = "approved"`
6. Implement the exception (e.g., enrol the late participant) → `state = "implemented"`, implementation_notes recorded
7. Close → `state = "closed"`
8. Create a second request; reject it → `state = "rejected"` → `state = "closed"`

**Key invariants**:
- Withdrawal only possible from `submitted`
- Approval/rejection only possible from `submitted`
- Implementation only possible from `approved`
- Closure only possible from `implemented` or `rejected`

---

### 📋 T-12: Data Import — Participant Bulk Import with Dry-Run Validation

- **File**: `sports_federation_import_tools/tests/test_tour_bulk_import.py`
- **Suite**: `competition_core`
- **Workflow**: `WORKFLOW_DATA_IMPORT.md`
- **Difficulty**: Medium
- **Dependencies**: `sports_federation_import_tools`

**Steps**:
1. Prepare a valid CSV payload (10 participants with team codes, club codes, seed)
2. Run dry-run → 0 errors, preview shows 10 rows `to_create`
3. Introduce a duplicate key row → dry-run flags 1 error
4. Fix CSV, re-run dry-run → clean
5. Commit import → 10 participants created in DB
6. Re-run import with the same CSV → idempotent, 0 new records created (duplicate keys skipped)
7. Run import with an invalid team code → dry-run catches the reference error before commit

**Key invariants**:
- Dry-run never writes to DB (tested via savepoint or record count comparison)
- Import key uniqueness is enforced at dry-run stage, not just commit
- Malformed rows produce field-level error messages (not generic crashes)

---

## Suggested Build Order

Based on inter-module dependencies and test value:

| Priority | Tour | Reason |
|----------|------|--------|
| 1 | T-02 Result Pipeline | Highest operator friction; result mistakes are costly |
| 2 | T-04 Roster Lifecycle | Prerequisite for match day operations |
| 3 | T-07 Discipline | Feeds into finance and suspension eligibility |
| 4 | T-08 Finance Events | Many workflows emit finance events; isolated and easy |
| 5 | T-06 Officiating | Completes the match day picture |
| 6 | T-03 Match Day Ops | Integrates rosters + officiating + results |
| 7 | T-05 Season Registration | End-to-end club onboarding |
| 8 | T-10 Compliance | Prerequisite for complete registration tour |
| 9 | T-11 Governance Override | Short, high-value safety net |
| 10 | T-09 Public Site | Requires controller/HTTP stack; run last |
| 11 | T-12 Data Import | Requires import wizard infrastructure |

---

## Per-Suite Assignment

| CI Suite | Tours |
|----------|-------|
| `competition_core` | T-01, T-02, T-05, T-12 |
| `people_rosters_rules` | T-03, T-04, T-06, T-07, T-10 |
| `finance_reporting` | T-08 |
| `release_surfaces` | T-09 |
| `ops_and_notifications` | T-11 |
