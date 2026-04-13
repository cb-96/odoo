# Sports Federation Rosters

Season and competition-bound team rosters plus match-day squad sheets. Controls
which players are eligible and available for each match, enforcing squad-size
limits from the applicable rule set and surfacing operator-readable readiness
feedback before rosters, participants, or match sheets move forward.

## Purpose

Provides a formal **roster** (the pool of players a team may select from for a
season or competition) and **match sheets** (the specific squad and starting
lineup for an individual match). Links to rule sets for squad-size validation
and to the shared eligibility service for license, registration, and suspension
checks.

## Dependencies

| Module | Reason |
|--------|--------|
| `sports_federation_base` | Clubs, teams, seasons |
| `sports_federation_people` | Players |
| `sports_federation_tournament` | Tournaments, matches |
| `sports_federation_rules` | Squad-size limits and player eligibility checks |
| `mail` | Chatter |

## Models

### `federation.team.roster`

A pool of eligible players for a team within a season or competition scope.

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Generated roster label |
| `team_id` | Many2one | Team |
| `season_id` | Many2one | Season scope |
| `season_registration_id` | Many2one | Linked registration |
| `competition_id` | Many2one | Competition scope (optional) |
| `rule_set_id` | Many2one | Squad-size rules |
| `status` | Selection | draft / active / closed |
| `valid_from` / `valid_to` | Date | Validity window |
| `line_ids` | One2many | Rostered players |
| `line_count` | Integer | Player count |
| `club_id` | Many2one (computed) | From team |
| `min_players_required` / `max_players_allowed` | Integer | From rule set |
| `ready_for_activation` | Boolean (computed) | Whether activation checks pass |
| `readiness_feedback` | Text (computed) | Aggregated activation blockers |
| `match_sheet_count` | Integer (computed) | Linked match sheets using this roster |
| `match_day_locked` | Boolean (computed) | Whether live match sheets now lock roster scope changes |
| `match_day_lock_feedback` | Text (computed) | Why the roster scope is locked |
| `audit_event_ids` | One2many | Participation audit events for this roster |

### `federation.team.roster.line`

A single player entry on a roster.

| Field | Type | Description |
|-------|------|-------------|
| `roster_id` | Many2one | Parent roster |
| `player_id` | Many2one | The player |
| `status` | Selection | active / inactive / suspended / removed |
| `date_from` / `date_to` | Date | Availability window |
| `jersey_number` | Char | Squad number |
| `is_captain` / `is_vice_captain` | Boolean | Leadership flags |
| `license_id` | Many2one | Explicit season license to validate |
| `eligible` | Boolean (computed) | Current eligibility status |
| `eligibility_feedback` | Text (computed) | Human-readable failure reasons |
| `notes` | Text | Remarks |

- **Match-day lock behaviour**: once a submitted, approved, or locked match sheet references a roster line, that referenced line cannot be structurally changed or removed.

### `federation.match.sheet`

The squad list submitted for a specific match.

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Sheet title |
| `match_id` | Many2one | The match |
| `team_id` | Many2one | Which team |
| `roster_id` | Many2one | Source roster |
| `side` | Selection | home / away |
| `state` | Selection | draft / submitted / approved / locked |
| `line_ids` | One2many | Player entries |
| `line_count` | Integer | Squad size |
| `ready_for_submission` | Boolean (computed) | Whether submission checks pass |
| `readiness_feedback` | Text (computed) | Aggregated submission blockers |
| `substitution_count` | Integer (computed) | Number of recorded substitution entries |
| `locked_on` / `locked_by_id` | Datetime / Many2one | Final lock metadata |
| `audit_event_ids` | One2many | Participation audit events for this sheet |
| `coach_name` / `manager_name` | Char | Team staff |
| `notes` | Text | Remarks |

- **State machine**: draft → submitted → approved → locked.

### `federation.match.sheet.line`

A player on a match sheet.

| Field | Type | Description |
|-------|------|-------------|
| `match_sheet_id` | Many2one | Parent sheet |
| `player_id` | Many2one | The player |
| `roster_line_id` | Many2one | Source roster line |
| `is_starter` | Boolean | In starting lineup |
| `is_substitute` | Boolean | Bench selection |
| `is_captain` | Boolean | Match captain |
| `jersey_number` | Char | Shirt number |
| `entered_minute` / `left_minute` | Integer | Substitution timeline tracking |
| `eligible` | Boolean (computed) | Current eligibility status |
| `eligibility_feedback` | Text (computed) | Human-readable failure reasons |
| `notes` | Text | Remarks |

### `federation.participation.audit`

Immutable operational log for roster and match-sheet activity.

| Field | Type | Description |
|-------|------|-------------|
| `event_type` | Selection | Created / updated / submitted / approved / locked / substitution events |
| `team_id` | Many2one | Team owning the event |
| `roster_id` | Many2one | Related season roster, when applicable |
| `match_sheet_id` | Many2one | Related match sheet, when applicable |
| `match_id` | Many2one | Related match, when applicable |
| `player_id` | Many2one | Player affected by the event |
| `description` | Text | Human-readable audit detail |
| `author_id` / `event_on` | Many2one / Datetime | Attribution and timestamp |

### `federation.tournament.participant` (extension)

This module extends tournament participants with team-linked roster readiness
checks. Tournament registration auto-provisions a team roster for the relevant
season and competition scope. Participants can still be confirmed and assigned
without a ready roster, but scheduled matches remain protected by the roster
deadline: one week before the first scheduled match, or one week before
tournament start if no match has been scheduled yet.

| Field | Type | Description |
|-------|------|-------------|
| `ready_for_confirmation` | Boolean (computed) | Whether the linked team currently satisfies the roster deadline rule |
| `roster_deadline_date` | Date (computed) | Deadline for having an active ready roster |
| `readiness_roster_id` | Many2one (computed) | Preferred team roster used for readiness checks |
| `confirmation_feedback` | Text (computed) | Warning or blocking message about the roster deadline |

## Key Behaviours

1. **Roster scoping** — Rosters are tied to a season and optionally a competition,
   preventing cross-competition player sharing.
2. **Eligibility-aware activation** — Roster activation is blocked until active
   lines satisfy date windows, squad-size bounds, and shared eligibility rules.
3. **Readable operator feedback** — Roster lines and match-sheet lines expose
   `eligibility_feedback`, while rosters and match sheets aggregate blockers into
   readiness summaries.
4. **Match sheet from roster** — Match sheets can validate against explicit
   roster lines so team, date-window, and license mismatches are caught early.
5. **Match-day locking** — Submitted and approved sheet activity locks roster
   scope changes and the referenced roster lines so historical lineups remain
   defensible.
6. **Substitution governance** — Approved sheets can record `entered_minute`
   and `left_minute` values while still blocking lineup changes after approval.
7. **Participation audit trail** — Roster lifecycle changes, lineup changes,
   submissions, approvals, locks, and substitutions are captured in
   `federation.participation.audit`.
8. **Participant roster readiness** — Tournament registration creates or reuses
   the relevant team roster automatically so roster maintenance stays attached
   to the participating team instead of requiring a separately named setup step.
9. **Operational roster deadline** — Tournament participants can still be
   confirmed and grouped without a ready roster, but scheduled matches keep the
   one-week roster deadline so operators cannot move into match-day workflows
   without an active ready roster.
10. **Team-linked roster checks** — Team roster lookup and tournament deadline
   assessment are owned by the team model so roster compliance follows the team
   rather than being treated as a separate participant-only concern.
11. **State locking** — Approved match sheets can be locked once match-day
   operations are complete.
