# Sports Federation Import Tools

Wizard-driven CSV import for clubs, seasons, teams, players, and tournament
participants. The module is intended for federation onboarding and annual
rollover work where administrators need rehearsable imports instead of raw ORM
loads.

## Purpose

The import wizards provide a safer operator workflow than direct list-imports:

- dry-run rehearsal before any records are created
- visible column mapping guidance in the wizard form
- code-first reference lookup where the target models expose stable codes
- categorized row-level failures instead of opaque batch errors
- duplicate-safe behavior that reports and skips existing records

The menu entry is available at Federation > Import Tools.

## Dependencies

| Module | Reason |
| ------ | ------ |
| `sports_federation_base` | Clubs, seasons, teams |
| `sports_federation_people` | Players |
| `sports_federation_tournament` | Tournament participants |

## Shared Wizard Behaviour

All import wizards inherit `federation.import.wizard.mixin`, which provides:

- UTF-8 and UTF-8 BOM CSV decoding
- comma or semicolon delimiter support
- shared `dry_run`, `mapping_guide`, `result_message`, `line_count`,
  `success_count`, and `error_count` fields
- standardized error categories such as `missing_reference`,
  `duplicate_entry`, `format_error`, and `missing_required_field`

## Supported Wizards

### `federation.import.clubs.wizard`

Required columns:

- `name`

Recommended columns:

- `code`, `email`, `phone`, `city`

Duplicate matching:

- `code` first, then exact club `name`

### `federation.import.seasons.wizard`

Required columns:

- `name`, `code`, `date_start`, `date_end`

Optional columns:

- `state`, `notes`

Validation notes:

- dates must use `YYYY-MM-DD`
- state must be one of `draft`, `open`, `closed`, `cancelled`

### `federation.import.teams.wizard`

Required columns:

- `team_name` or `name`
- `club_code` or `club_name`

Recommended columns:

- `code`, `category`, `gender`, `email`, `phone`

Duplicate matching:

- `code` first, then `(club_id, name)`

### `federation.import.players.wizard`

Required columns:

- `first_name` and `last_name`
- legacy imports may use `name` when it contains both parts of the full name

Recommended columns:

- `birth_date`, `club_code` or `club_name`, `gender`, `email`, `phone`, `state`

Validation notes:

- `birth_date` must use `YYYY-MM-DD`
- duplicate detection follows the player uniqueness key:
  `(first_name, last_name, birth_date)`

### `federation.import.tournament.participants.wizard`

Required columns:

- `tournament_code` or `tournament_name`
- `team_code` or `team_name`

Optional columns:

- `seed`

Validation notes:

- team eligibility and duplicate participation reuse the same tournament-side
  checks as manual participant creation

## Operational Behaviour

1. Dry-run imports validate every row and never create records.
2. Real imports create valid rows and keep processing after row-level failures.
3. Existing records are not overwritten; duplicates are reported and skipped.
4. Result summaries include both totals and categorized error counts so
   administrators can fix the source CSV predictably.
