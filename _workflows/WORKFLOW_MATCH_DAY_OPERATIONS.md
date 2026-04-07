# Workflow: Match Day Operations

Everything that happens around a single match — roster management, match-sheet
submission, referee assignment, and match execution.

## Overview

On match day, several parallel preparation streams converge: the team rosters
must be active, match sheets must be submitted with eligible players, referees
must be assigned and confirmed, and the venue must be set. This workflow covers
the operational sequence from pre-match preparation through to the final whistle.

## Modules Involved

| Module | Role |
|--------|------|
| `sports_federation_rosters` | Season rosters and match-day squad sheets |
| `sports_federation_officiating` | Referee assignment to matches |
| `sports_federation_venues` | Venue and playing-area assignment |
| `sports_federation_tournament` | Match record management |
| `sports_federation_people` | Player eligibility verification |
| `sports_federation_rules` | Squad-size limits and eligibility rules |
| `sports_federation_discipline` | Suspension checks |

## Step-by-Step Flow

### 1. Roster Preparation (Pre-Season)

**Actor**: Club administrator or federation staff
**Module**: `sports_federation_rosters`

1. Create a **team roster** for the season/competition.
2. Link to the team, season, and optionally the competition and rule set.
3. Add **roster lines** — each line is a player with role (player/captain/vice_captain).
4. Validate squad size against rule-set limits (min/max players).
5. Set roster status: `draft` → `active`.
6. An active roster is the pool from which match sheets draw players.

### 2. Match Sheet Creation

**Actor**: Club administrator or team manager
**Module**: `sports_federation_rosters`

1. For each match, create a **match sheet** for each participating team (home/away).
2. Link the match sheet to the match, team, and source roster.
3. Set the side (`home` or `away`).
4. Add **match sheet lines** — select players from the active roster.
5. Mark starters vs. substitutes (`is_starter` flag).
6. Assign jersey numbers and positions.
7. Add coach and manager names.
8. Validate: check that selected players are on the active roster, not suspended,
   and hold valid licenses.

Match sheet states: `draft` → `submitted` → `confirmed` → `locked`.

### 3. Referee Assignment

**Actor**: Federation referee coordinator
**Module**: `sports_federation_officiating`

1. Select referees from the registry based on certification level and availability.
2. Create **match referee** assignments with defined roles:
   - `head` — Main referee
   - `assistant` — Assistant referees
   - `fourth` — Fourth official
   - `var` — Video assistant (if applicable)
3. Each assignment has a state: `assigned` → `confirmed` → `completed` / `cancelled`.
4. SQL constraint prevents duplicate (match, referee, role) combinations.
5. The rule set's `referee_required_count` indicates how many officials are needed.

### 4. Venue Confirmation

**Actor**: Federation administrator
**Module**: `sports_federation_venues`

1. Confirm the match venue is set (via `venue_id` on the match).
2. Verify the playing area is available and suitable.
3. Contact venue via stored contact details if needed.
4. If the venue incurs passthrough costs, create a finance event for the
   booking: use the **Create Venue Charge** button on the match header (visible
   when the match is `scheduled`) or call the programmatic helper
   `match.action_create_venue_finance_event()` (fee type code `venue_booking` by default).
5. Gameday bundling and constraints:
    - Matches may be attached to a `federation.gameday` record (`match.gameday_id`).
       When schedules are generated with `Schedule By Round`, the scheduler
       creates or finds a `gameday` per round and attaches the matches. This
       groups matches at a venue/day for operational coordination (referees,
       volunteers, venue logistics and finance events).
    - The venues module enforces a constraint that prevents teams in the same
       `category` from playing the same opponent more than once on the same
       gameday. This avoids repeated pairings in the same venue/day block.
    - For programmatic creation or lookup use the gameday helper in
       `sports_federation_venues.models.federation_gameday` (e.g. `find_or_create`).

### 5. Pre-Match Checks

**Actor**: Federation staff
**Modules**: Multiple

Before the match starts, verify:

| Check | Module | Detail |
|-------|--------|--------|
| Match sheets submitted | `rosters` | Both teams have confirmed sheets |
| Squad sizes valid | `rules` | Within min/max from rule set |
| Player licenses active | `people` | All listed players have active season licenses |
| No active suspensions | `discipline` | No player on the sheet is currently suspended |
| Referees confirmed | `officiating` | Required referee roles are filled and confirmed |
| Venue set | `venues` | Match has a valid venue assignment |

### 6. Match Execution

**Actor**: Referees, federation staff
**Module**: `sports_federation_tournament`

1. Set match state to `in_progress` at kick-off.
2. During the match, record:
   - Substitutions (update `substitution_minute` on match sheet lines)
   - Incidents (yellow/red cards, misconduct) → feeds into discipline workflow
3. At full time, enter final scores (`home_score`, `away_score`).
4. Set match state to `completed`.

### 7. Post-Match Actions

**Actor**: Various
**Modules**: Multiple

After the match completes:

| Action | Module | Detail |
|--------|--------|--------|
| Lock match sheets | `rosters` | Sheets move to `locked` state |
| Complete referee assignments | `officiating` | Assignments marked `completed` |
| Submit result for verification | `result_control` | Feeds into result pipeline |
| Record incidents | `discipline` | Incidents logged during match |
| Log finance events | `finance_bridge` | Referee reimbursements, venue booking charges (via match header), any fines |
| Recompute standings | `standings` | Updated with new result |

## State Diagram

```
Roster: draft → active → locked → archived

Match Sheet: draft → submitted → confirmed → locked

Referee Assignment: assigned → confirmed → completed
                                          → cancelled

Match: draft → scheduled → in_progress → completed
                                        → cancelled
```

## Typical Timeline

| Timing | Action |
|--------|--------|
| Pre-season | Create and activate team rosters |
| 1 week before | Assign referees to match |
| 48 hours before | Confirm referee assignments |
| 24 hours before | Submit match sheets |
| Match day | Confirm match sheets, verify eligibility |
| Kick-off | Set match to in_progress |
| Full time | Enter scores, log incidents |
| Post-match | Lock sheets, submit result, update standings |

## Related Workflows

- [Result Pipeline](WORKFLOW_RESULT_PIPELINE.md) — what happens after score entry
- [Discipline Pipeline](WORKFLOW_DISCIPLINE_PIPELINE.md) — incident follow-up
- [Tournament Lifecycle](WORKFLOW_TOURNAMENT_LIFECYCLE.md) — tournament-level context
