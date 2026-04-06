# Sports Federation Rosters

Season and competition-bound team rosters plus match-day squad sheets. Controls
which players are eligible and available for each match, enforcing squad-size
limits from the applicable rule set.

## Purpose

Provides a formal **roster** (the pool of players a team may select from for a
season or competition) and **match sheets** (the specific squad and starting
lineup for an individual match). Links to rule sets for squad-size validation.

## Dependencies

| Module | Reason |
|--------|--------|
| `sports_federation_base` | Clubs, teams, seasons |
| `sports_federation_people` | Players |
| `sports_federation_tournament` | Tournaments, matches |
| `sports_federation_rules` | Squad-size limits |
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

### `federation.team.roster.line`

A single player entry on a roster.

| Field | Type | Description |
|-------|------|-------------|
| `roster_id` | Many2one | Parent roster |
| `player_id` | Many2one | The player |
| `is_active` | Boolean | Currently active on roster |
| `date_from` / `date_to` | Date | Availability window |
| `role` | Selection | player / captain / vice_captain |
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
| `state` | Selection | draft / submitted / confirmed / locked |
| `line_ids` | One2many | Player entries |
| `line_count` | Integer | Squad size |
| `coach_name` / `manager_name` | Char | Team staff |
| `notes` | Text | Remarks |

- **State machine**: draft → submitted → confirmed → locked.

### `federation.match.sheet.line`

A player on a match sheet.

| Field | Type | Description |
|-------|------|-------------|
| `match_sheet_id` | Many2one | Parent sheet |
| `player_id` | Many2one | The player |
| `is_starter` | Boolean | In starting lineup |
| `jersey_number` | Integer | Shirt number |
| `position` | Selection | goalkeeper / defender / midfielder / forward / other |
| `substitution_minute` | Integer | Minute of substitution |
| `is_suspended` | Boolean | Flagged as suspended |
| `notes` | Text | Remarks |

## Key Behaviours

1. **Roster scoping** — Rosters are tied to a season and optionally a competition,
   preventing cross-competition player sharing.
2. **Match sheet from roster** — Match sheets pull players from the team's active
   roster.
3. **Squad-size validation** — Rule-set limits are applied to roster line counts.
4. **State locking** — Confirmed match sheets cannot be modified.
