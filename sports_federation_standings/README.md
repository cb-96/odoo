# Sports Federation Standings

Computes and stores league-style standings tables for tournament stages and groups.
Aggregates match results into a ranked table with points, wins, losses, goal
differences, and configurable tie-break ordering.

## Purpose

Provides a **snapshot** of competition standings that can be published, audited,
and used by downstream modules (public site, reporting, qualification engine).
Standings are linked to rule sets to ensure consistent scoring and tie resolution.

## Dependencies

| Module | Reason |
|--------|--------|
| `sports_federation_tournament` | Tournaments, stages, groups, matches |
| `sports_federation_rules` | Rule sets for scoring and tie-breaks |
| `mail` | Chatter integration |

## Models

### `federation.standing`

A standings table for a specific scope (tournament, stage, or group).

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Standings title |
| `tournament_id` | Many2one | Tournament |
| `stage_id` | Many2one | Stage scope (optional) |
| `group_id` | Many2one | Group scope (optional) |
| `competition_id` | Many2one | Competition context |
| `rule_set_id` | Many2one | Scoring and tie-break rules |
| `state` | Selection | draft / computed / published |
| `line_ids` | One2many | Ranked team entries |
| `line_count` | Integer | Stat-button counter |
| `computed_on` | Datetime | When last computed |
| `notes` | Text | Additional notes |

- **State machine**: draft → computed → published.

### `federation.standing.line`

One row per participant in the standings table.

| Field | Type | Description |
|-------|------|-------------|
| `standing_id` | Many2one | Parent standings |
| `participant_id` | Many2one | The team |
| `position` | Integer | Current rank |
| `matches_played` | Integer | Total games |
| `wins` / `draws` / `losses` | Integer | Results breakdown |
| `goals_for` / `goals_against` | Integer | Goal statistics |
| `goal_difference` | Integer (computed) | goals_for − goals_against |
| `points` | Integer | Total points per rule set |
| `notes` | Text | Remarks |

## Key Behaviours

1. **Rule-set driven scoring** — Points are calculated using the attached rule set
   (win/draw/loss values).
2. **Tie-break resolution** — When teams have equal points, tie-break rules from the
   rule set are applied in sequence order.
3. **Snapshot model** — Each standings record is a point-in-time computation, allowing
   historical comparison.
4. **Publication flow** — draft → computed (results aggregated) → published (visible
   to public site).
