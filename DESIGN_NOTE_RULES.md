# Design Note: sports_federation_rules

## Purpose

The `sports_federation_rules` module provides a **competition rules and configuration layer** that allows competitions, standings, scheduling, eligibility, and validation logic to depend on configurable data instead of hardcoded Python assumptions.

## Architecture

### Core Models

1. **`federation.competition`** — Defines a competition independently from a tournament.
   - Can be linked to a season and a rule set.
   - Has a state machine: draft → active → closed.
   - One2many to tournaments that reference this competition.

2. **`federation.rule.set`** — A reusable collection of rules that can be applied to competitions.
   - Contains default points (win/draw/loss) as simple Integer fields.
   - One2many to `federation.points.rule` for extended result types (bye, forfeit, etc.).
   - One2many to `federation.tie_break.rule` for ordered tie-break criteria.
   - One2many to `federation.eligibility.rule` for player/team eligibility checks.
   - One2many to `federation.qualification.rule` for stage progression logic.
   - Configures squad size limits, referee requirements, and seeding mode.

3. **`federation.points.rule`** — Maps result types (win, draw, loss, bye, forfeit) to points.
   - Unique constraint per rule set and result type.

4. **`federation.tie_break.rule`** — Ordered list of tie-break criteria.
   - Sequence-based ordering.
   - Supports: head-to-head, goal difference, goals scored, goals against, fair play, drawing of lots, ranking points, custom.
   - Unique constraint per rule set and tie-break type.

5. **`federation.eligibility.rule`** — Schema foundation for eligibility checks.
   - Types: age_min, age_max, gender, license_valid, suspension, registration, custom.
   - Has `is_placeholder` flag for future implementation rules.
   - Age and category fields for type-specific constraints.

6. **`federation.qualification.rule`** — Foundation for stage progression logic.
   - Types: top_n, top_percent, min_points, min_position, group_winner, group_runner_up, custom.
   - Has `target_stage_id` (extension point) for linking to tournament stages.

### Relationships to Existing Modules

#### `federation.tournament` (sports_federation_tournament)
- Added `competition_id` Many2one → `federation.competition`
- Added `rule_set_id` Many2one → `federation.rule.set`
- Updated form view to display these fields

#### `federation.season.registration` (sports_federation_base)
- Added `competition_id` Many2one → `federation.competition`
- Added `rule_set_id` Many2one → `federation.rule.set`
- Updated form, tree, and search views

### Security

- Reuses existing `group_federation_user` and `group_federation_manager` from `sports_federation_base`.
- Users can read all rule configurations.
- Managers can create, update, and delete.
- No portal or public access.

## How Later Modules Should Depend on This

### Standings Computation Module
A future `sports_federation_standings` module should:

1. Read `rule_set_id` from the tournament or competition.
2. Use `points_rule_ids` or the simple `points_win/draw/loss` fields to calculate standings.
3. Apply `tie_break_rule_ids` in sequence order when teams are level on points.
4. Use `qualification_rule_ids` to determine which teams advance to the next stage.

### Scheduling Module
A future `sports_federation_scheduling` module should:

1. Read `squad_min_size` and `squad_max_size` from the rule set to validate registrations.
2. Read `referee_required_count` to check match readiness.
3. Use `seeding_mode` to determine initial draw/seeding for tournament groups.

### Eligibility Validation Module
A future module or service should:

1. Iterate `eligibility_rule_ids` from the rule set.
2. For each rule, check the player/team against the constraint.
3. Skip rules marked `is_placeholder = True` (log a warning instead).
4. Raise validation errors for active, non-placeholder rules that fail.

### Example: Reading Points Configuration

```python
# In a standings computation service
def get_points_for_result(self, tournament, result_type):
    rule_set = tournament.rule_set_id
    if not rule_set:
        # Fallback to defaults
        defaults = {"win": 3, "draw": 1, "loss": 0}
        return defaults.get(result_type, 0)
    
    # Check explicit points rules first
    points_rule = rule_set.points_rule_ids.filtered(
        lambda r: r.result_type == result_type
    )
    if points_rule:
        return points_rule.points
    
    # Fallback to default fields
    if result_type == "win":
        return rule_set.points_win
    elif result_type == "draw":
        return rule_set.points_draw
    elif result_type == "loss":
        return rule_set.points_loss
    return 0
```

### Example: Applying Tie-Break Rules

```python
def apply_tie_break(self, rule_set, teams_with_points):
    """Apply tie-break rules in sequence order."""
    if not rule_set or not rule_set.tie_break_rule_ids:
        return teams_with_points
    
    for tie_break in rule_set.tie_break_rule_ids.sorted("sequence"):
        teams_with_points = self._apply_single_tie_break(
            tie_break, teams_with_points
        )
        # If all ties are resolved, stop
        if self._no_ties_remain(teams_with_points):
            break
    
    return teams_with_points
```

## Known Limitations

1. **No automatic standings computation** — This module only stores configuration. A separate module is needed to compute standings.
2. **No schedule generation** — Rule set configuration does not generate match schedules.
3. **Eligibility rules are schema-only** — The `is_placeholder` field marks rules that are documented but not yet enforced by code.
4. **Qualification rules lack automation** — The `target_stage_id` field is an extension point; no code currently moves teams between stages based on qualification rules.

## Installation/Upgrade Steps

1. Install `sports_federation_base` first (dependency).
2. Install `sports_federation_rules`.
3. The module will add `competition_id` and `rule_set_id` fields to `federation.tournament` and `federation.season.registration` automatically.
4. Existing tournaments and registrations will have these fields set to NULL (no data migration needed).

## Future Extension Points

- `federation.eligibility.rule.is_placeholder` — When implementing enforcement, check this flag and skip placeholder rules.
- `federation.qualification.rule.target_stage_id` — Use this to automatically advance teams to the correct stage.
- `federation.rule.set.competition_ids` — Reverse relation for finding which competitions use a given rule set.
- `federation.points.rule` result types — Add more result types (e.g., `technical_win`, `walkover`) as needed.
- `federation.tie_break.rule.reverse_order` — Used for criteria where lower is better (e.g., fewer goals against).