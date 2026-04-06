# Sports Federation Rules

Competition rule configuration layer. Defines reusable **rule sets** with scoring
tables, tie-break criteria, eligibility requirements, and qualification rules —
all as configurable data rather than hard-coded logic.

## Purpose

Decouples competition logic from code. Any competition or tournament can reference
a rule set, and modules like Standings, Competition Engine, and Rosters consume
these rules to compute points, resolve ties, validate squads, and determine
progression.

## Dependencies

| Module | Reason |
|--------|--------|
| `sports_federation_base` | Core entities |

## Models

### `federation.rule.set`

A named, reusable collection of rules. Attach it to a competition or tournament
to govern how that event works.

| Field | Type | Description |
|-------|------|-------------|
| `name` / `code` | Char | Identity (code is unique) |
| `description` | Text | Human-readable explanation |
| `points_win` / `points_draw` / `points_loss` | Integer | Default scoring |
| `points_rule_ids` | One2many | Extended result-type scoring |
| `tie_break_rule_ids` | One2many | Ordered tie-break criteria |
| `eligibility_rule_ids` | One2many | Player/team eligibility |
| `qualification_rule_ids` | One2many | Stage progression logic |
| `squad_min_size` / `squad_max_size` | Integer | Roster limits |
| `referee_required_count` | Integer | Officials needed per match |
| `seeding_mode` | Selection | How participants are seeded |

### `federation.points.rule`

Maps a result type to a point value within a rule set.

| Field | Type | Description |
|-------|------|-------------|
| `rule_set_id` | Many2one | Parent rule set |
| `result_type` | Selection | win / draw / loss / bye / forfeit |
| `points` | Integer | Points awarded |

- **Unique constraint**: one entry per (rule_set, result_type).

### `federation.tie_break_rule`

Ordered criteria to resolve teams with equal points.

| Field | Type | Description |
|-------|------|-------------|
| `rule_set_id` | Many2one | Parent rule set |
| `sequence` | Integer | Priority order |
| `tie_break_type` | Selection | head_to_head / goal_difference / goals_scored / goals_against / fair_play / drawing_lots / ranking_points / custom |
| `description` | Char | Label |
| `reverse_order` | Boolean | Invert sort direction |

### `federation.eligibility.rule`

Defines who is allowed to participate.

| Field | Type | Description |
|-------|------|-------------|
| `rule_set_id` | Many2one | Parent rule set |
| `sequence` | Integer | Evaluation order |
| `name` | Char | Rule label |
| `eligibility_type` | Selection | age_min / age_max / gender / license_valid / suspension / registration / custom |
| `age_limit` | Integer | For age-based rules |
| `allowed_categories` | Char | Comma-separated category codes |
| `is_placeholder` | Boolean | Not yet implemented |

### `federation.qualification.rule`

Determines how teams advance between stages.

| Field | Type | Description |
|-------|------|-------------|
| `rule_set_id` | Many2one | Parent rule set |
| `sequence` | Integer | Evaluation order |
| `name` | Char | Rule label |
| `qualification_type` | Selection | top_n / top_percent / min_points / min_position / group_winner / group_runner_up / custom |
| `value_integer` / `value_percent` | Number | Threshold values |
| `target_stage_id` | Char | Extension point for stage linking |

## Key Behaviours

1. **Reusable rule sets** — One rule set can be shared by many competitions.
2. **Configurable scoring** — Default win/draw/loss points plus extended result types.
3. **Ordered tie-breaks** — Sequence-based priority resolves equal points systematically.
4. **Placeholder eligibility** — Rules can be defined structurally before enforcement
   logic is implemented.
