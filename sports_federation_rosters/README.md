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
| `name` | Char | Roster title |
| `team_id` | Many2one | Team |
| `season_id` | Many2one | Season scope |
| `season_registration_id` | Many2one | Linked registration |
| `competition_id` | Many2one | Competition scope (optional) |
| `rule_set_id` | Many2one | Squad-size rules |
| `status` | Selection | draft / active / locked / archived |
| `valid_from` / `valid_to` | Date | Validity window |
| `line_ids` | One2many | Rostered players |
| `line_count` | Integer | Player count |
| `club_id` | Many2one (computed) | From team |
| `min_players_required` / `max_players_allowed` | Integer | From rule set |
| `ready_for_activation` | Boolean (computed) | Whether activation checks pass |
| `readiness_feedback` | Text (computed) | Aggregated activation blockers |

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
| `eligible` | Boolean (computed) | Current eligibility status |
| `eligibility_feedback` | Text (computed) | Human-readable failure reasons |
| `notes` | Text | Remarks |

### `federation.tournament.participant` (extension)

This module extends tournament participants so confirmation is blocked until a
team has an active, ready roster for the tournament season.

| Field | Type | Description |
|-------|------|-------------|
| `ready_for_confirmation` | Boolean (computed) | Whether participant confirmation checks pass |
| `readiness_roster_id` | Many2one (computed) | Active roster used for confirmation checks |
| `confirmation_feedback` | Text (computed) | Aggregated confirmation blockers |

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
5. **Participant confirmation gating** — Tournament participants can only be
   confirmed when an active ready roster exists for the tournament season,
   preferring competition-specific rosters when available.
6. **State locking** — Approved match sheets can be locked once match-day
   operations are complete.
