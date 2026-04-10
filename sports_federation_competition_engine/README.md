# Sports Federation Competition Engine

Schedule generation wizards for **round-robin** and **knockout** formats. Given a
tournament with participants, the engine creates all matches, assigns venues, and
sets date/times automatically.

## Purpose

Automates the creation of match fixtures. Instead of manually entering dozens or
hundreds of matches, federation staff run a wizard that generates a complete
schedule respecting the chosen format, seeding, and time intervals.

## Dependencies

| Module | Reason |
|--------|--------|
| `sports_federation_tournament` | Tournaments, stages, groups, participants, matches |

## Wizards

### `federation.round.robin.wizard`

Generates a full round-robin schedule where every participant plays every other
participant once (or twice in a double round-robin).

| Field | Type | Description |
|-------|------|-------------|
| `tournament_id` | Many2one | Target tournament |
| `stage_id` | Many2one | Target stage |
| `group_id` | Many2one | Target group (optional) |
| `participant_ids` | Many2many | Teams to schedule |
| `use_all_participants` | Boolean | Use all enrolled participants |
| `round_type` | Selection | single / double |
| `start_datetime` | Datetime | First match kick-off |
| `interval_hours` | Integer | Hours between rounds |
| `venue` | Char | Default venue |
| `overwrite` | Boolean | Allow replacing existing matches |
| `summary` | Text (computed) | Preview of what will be generated |

**Algorithm**: Circle method ensuring no team plays itself and every pair meets
exactly once (or twice for double). Handles odd participant counts with automatic
bye rounds. Matches are created with deterministic ordering.

### `federation.knockout.wizard`

Generates a single-elimination bracket.

| Field | Type | Description |
|-------|------|-------------|
| `tournament_id` | Many2one | Target tournament |
| `stage_id` | Many2one | Target stage |
| `participant_source` | Selection | manual / from_stage |
| `participant_ids` | Many2many | Manually selected teams |
| `source_stage_id` | Many2one | Pull from previous stage standings |
| `seeding` | Selection | natural / power_of_two |
| `bracket_size` | Selection | 4 / 8 / 16 / 32 |
| `start_datetime` | Datetime | First match kick-off |
| `interval_hours` | Integer | Hours between rounds |
| `venue` | Char | Default venue |
| `overwrite` | Boolean | Allow replacing existing matches |
| `summary` | Text (computed) | Bracket preview |

**Algorithm**: Generates seeded brackets, handles byes when participant count
is not a power of two, and ensures top seeds are separated. Power-of-two seeding
follows standard tournament bracket placement.

## Key Behaviours

1. **Overwrite protection** — Existing matches are preserved unless `overwrite` is
   explicitly checked.
2. **Tournament state check** — Wizards enforce that the tournament is in the correct
   state (open or in_progress) before generating.
3. **Rule-set requirement** — Wizard-driven generation requires an effective rule set on the tournament or linked competition before fixtures can be created.
4. **Preview-first UI** — Both wizards show a computed preview summary before confirmation and display an explicit warning when overwrite mode is enabled.
5. **Minimum participants** — At least 2 teams are required.
6. **Tournament templates** — `federation.tournament.template.action_apply()` scaffolds stages, groups, and progression rules and now has regression coverage.
7. **Button integration** — Wizard launch buttons are added to the tournament form view.
