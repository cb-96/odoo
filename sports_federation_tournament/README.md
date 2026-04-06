# Sports Federation Tournament

Tournament lifecycle management — from creation through scheduling to completion.
Provides the structural backbone for all competitive activity: tournaments, stages,
groups, participants, and matches.

## Purpose

Models the full **tournament hierarchy**: a tournament is divided into stages
(e.g. group phase, quarter-finals), stages contain groups, and groups contain
matches between participants. This module is the central hub that most
competition-related modules extend.

## Dependencies

| Module | Reason |
|--------|--------|
| `sports_federation_base` | Clubs, teams, seasons |
| `sports_federation_rules` | Rule sets, competitions |

## Models

### `federation.competition`

A named competition series (e.g. "National League Division 1") that may span
multiple seasons and link to a rule set.

| Field | Type | Description |
|-------|------|-------------|
| `name` / `code` | Char | Competition identity |
| `season_id` | Many2one | Governing season |
| `rule_set_id` | Many2one | Applicable rule set |
| `state` | Selection | draft / active / closed |
| `tournament_ids` | One2many | Tournaments under this competition |

### `federation.tournament`

A single tournament event within a competition or season.

| Field | Type | Description |
|-------|------|-------------|
| `name` / `code` | Char | Tournament identity |
| `season_id` | Many2one | Season context |
| `competition_id` | Many2one | Parent competition |
| `rule_set_id` | Many2one | Rules (inherited from competition or set directly) |
| `tournament_type` | Selection | league / cup / friendly / playoff |
| `state` | Selection | draft / open / in_progress / completed / cancelled |
| `date_start` / `date_end` | Date | Event window |
| `max_participants` | Integer | Participant cap |
| `stage_ids` | One2many | Tournament stages |
| `participant_ids` | One2many | Enrolled participants |
| `match_ids` | One2many | All matches across stages |

- **State machine**: draft → open → in_progress → completed / cancelled.
- **Stat buttons** for stages, participants, and matches.

### `federation.tournament.stage`

A phase or round within a tournament (e.g. "Group Phase", "Semi-finals").

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Stage label |
| `tournament_id` | Many2one | Parent tournament |
| `stage_type` | Selection | group / knockout / playoff / other |
| `sequence` | Integer | Natural ordering |
| `date_start` / `date_end` | Date | Stage window |
| `group_ids` | One2many | Groups within this stage |
| `match_ids` | One2many | Matches in this stage |

### `federation.tournament.group`

A subdivision within a stage (e.g. "Group A", "Pool 1").

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Group label |
| `stage_id` | Many2one | Parent stage |
| `tournament_id` | Many2one | Computed from stage |
| `sequence` | Integer | Natural ordering |
| `max_participants` | Integer | Group capacity |
| `participant_ids` | One2many | Teams in this group |
| `match_ids` | One2many | Group matches |

### `federation.tournament.participant`

Links a team to a tournament, optionally assigned to a specific stage and group.

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char (computed) | Team name in tournament context |
| `tournament_id` | Many2one | Tournament |
| `team_id` | Many2one | The team |
| `club_id` | Many2one | Computed from team |
| `stage_id` / `group_id` | Many2one | Assignment |
| `seed` | Integer | Seeding rank |
| `registration_date` | Date | When enrolled |
| `state` | Selection | registered / confirmed / withdrawn / eliminated |

### `federation.match`

An individual game between two teams.

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char (computed) | "Home vs Away" |
| `tournament_id` | Many2one | Tournament |
| `stage_id` / `group_id` | Many2one | Location in hierarchy |
| `home_team_id` / `away_team_id` | Many2one | Competing teams |
| `date_scheduled` | Datetime | Kick-off time |
| `venue` | Char | Playing location |
| `home_score` / `away_score` | Integer | Final score |
| `state` | Selection | draft / scheduled / in_progress / completed / cancelled |

- **State machine**: draft → scheduled → in_progress → completed / cancelled.

## Key Behaviours

1. **Hierarchical structure** — Tournament → Stage → Group → Match.
2. **Participant tracking** — Teams enrol in a tournament and are placed into stages/groups.
3. **Score entry** — Match results are recorded with home/away scores.
4. **State management** — Both tournaments and matches follow state machines that
   prevent illogical transitions.
