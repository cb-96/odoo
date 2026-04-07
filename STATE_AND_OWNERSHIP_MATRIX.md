# State & Ownership Matrix

This document is the canonical reference for lifecycle states and role-based
ownership across the four core domain objects of the Sports Federation Platform.
It is generated from the live codebase and must be updated whenever a state,
field, or role changes.

---

## 1. `federation.tournament`

**Module**: `sports_federation_tournament`

| State | Label | Who Sets It | Allowed Transitions | Constraints / Notes |
|---|---|---|---|---|
| `draft` | Draft | System (default on create) | → `open` | Editable; no matches can be scheduled |
| `open` | Open | Federation Manager | → `in_progress`, `cancelled` | Participants can register |
| `in_progress` | In Progress | Federation Manager | → `closed`, `cancelled` | Matches may be generated and played |
| `closed` | Closed | Federation Manager | — | Terminal state; standings may be frozen |
| `cancelled` | Cancelled | Federation Manager | — | Terminal state; all matches become void |

**Ownership rules**:
- Federation Manager group may set any state.
- Club Managers may read but cannot change `state`.
- Public users see only `open` and `in_progress` tournaments when `website_published = True`.

---

## 2. `federation.match`

**Module**: `sports_federation_tournament` (base match state) and
`sports_federation_result_control` (result pipeline overlay)

### 2a. Match lifecycle state (`state` field)

| State | Label | Who Sets It | Allowed Transitions | Notes |
|---|---|---|---|---|
| `draft` | Draft | System | → `scheduled`, `cancelled` | Auto‑created by generation service |
| `scheduled` | Scheduled | Federation Manager | → `in_progress`, `cancelled` | Date and venue assigned |
| `in_progress` | In Progress | Referee / Match Official | → `done`, `cancelled` | Scores may be entered |
| `done` | Done | System / Manager (action_done) | — | Scores locked; triggers bracket advance if applicable |
| `cancelled` | Cancelled | Federation Manager | — | Does not count in standings |

### 2b. Result review pipeline (`result_state` field — added by `sports_federation_result_control`)

| State | Label | Who Sets It | Allowed Transitions | Notes |
|---|---|---|---|---|
| `draft` | Draft | System (default) | → `submitted` | Scores editable |
| `submitted` | Submitted | Club / Referee | → `verified`, `contested` | Scores are locked for editing |
| `verified` | Verified | Verifier role | → `approved`, `contested` | Pre‑approval check passed |
| `approved` | Approved | Approver role | → `contested`, `corrected` | Sets `include_in_official_standings = True` |
| `contested` | Contested | Approver / Club | → `corrected` | Requires `result_contest_reason`; clears official standings flag |
| `corrected` | Corrected | Approver | → (manual re-approve or stays corrected) | Requires `result_correction_reason` |

> **Standings safety rule**: Only matches with `include_in_official_standings = True`
> (set automatically on `approved`) count in standings computation.  
> `standings.py` checks for this field's presence at runtime — when
> `sports_federation_result_control` is installed it is automatically applied.

---

## 3. `federation.tournament.participant`

**Module**: `sports_federation_tournament`

| State | Label | Who Sets It | Allowed Transitions | Notes |
|---|---|---|---|---|
| `registered` | Registered | System (default) / Club | → `confirmed`, `withdrawn` | Initial registration; subject to eligibility checks |
| `confirmed` | Confirmed | Federation Manager | → `withdrawn` | Eligibility satisfied; participant can compete |
| `withdrawn` | Withdrawn | Club / Federation Manager | — | Team removed from tournament; any assigned matches stay (may need cancellation) |

**Ownership rules**:
- Club Managers may submit registration (create participant record).
- Federation Manager confirms or withdraws.
- Withdrawal does not automatically cancel existing matches — this must be done manually or via wizard.

---

## 4. `federation.standing`

**Module**: `sports_federation_standings`

| State | Label | Who Sets It | Allowed Transitions | Notes |
|---|---|---|---|---|
| `draft` | Draft | System (default) | → `computed`, `frozen` | No lines; empty table |
| `computed` | Computed | `action_recompute()` | → `frozen`, `draft` (via unfreeze) | Lines reflect current approved results |
| `frozen` | Frozen | `action_freeze()` | → `computed` (via `action_unfreeze`) | Results are locked; triggers `auto_advance` progressions from `sports_federation_competition_engine` |

**Recompute safety**:
- Frozen standings reject `action_recompute()` unless context key `force_recompute` is set.
- `action_freeze()` triggers any `federation.stage.progression` rules with `auto_advance = True` for the standing's stage/group.

---

## 5. `federation.stage.progression`

**Module**: `sports_federation_competition_engine`

| State | Label | Who Sets It | Allowed Transitions | Notes |
|---|---|---|---|---|
| `pending` | Pending | System (default) | → `executed`, `cancelled` | Auto-advance triggers on standings freeze |
| `executed` | Executed | `action_execute()` | — | Terminal; participants have been advanced |
| `cancelled` | Cancelled | Federation Manager | — | Terminal; no participants advanced |

---

## Ownership Summary Table

| Object | Create | Read | Edit state | Freeze / Close | Public visibility |
|---|---|---|---|---|---|
| `federation.tournament` | Manager | All roles | Manager | Manager | `website_published` flag |
| `federation.match` | Manager / Generator service | All roles | Referee (in_progress), Manager | Auto on `done` | Result published when `result_state = approved` |
| `federation.tournament.participant` | Club Manager | All roles | Club + Manager | Manager | Via tournament visibility |
| `federation.standing` | Manager | All roles | Manager (action_recompute) | Manager (action_freeze) | `website_published` flag on standing |
| `federation.stage.progression` | Manager / Template | Manager | Engine service | Auto on executed | n/a |

---

## Lifecycle Diagram (textual)

```
Tournament:    draft ──> open ──> in_progress ──> closed
                                 └──────────────> cancelled

Match state:   draft ──> scheduled ──> in_progress ──> done
                                        └──────────────> cancelled

Match result:  draft ──> submitted ──> verified ──> approved ──> [official standings]
                                  ╰──> contested ──> corrected
                                  ╰──────────────────────────╯

Participant:   registered ──> confirmed ──> [plays]
                         └──> withdrawn

Standing:      draft ──> computed ──> frozen ──> [auto-advance progression]
                         ╰──── unfreeze ─────╯
```

---

_Last updated by: Phase 1 stabilization (automated) — update this file when any state machine changes._
