# Sports Federation Import Tools

Wizard-driven CSV import for clubs, teams, players, and tournament participants.
Provides a guided, validated import experience with dry-run preview and detailed
error reporting.

## Purpose

Enables bulk data loading during federation setup or season transitions. Rather
than manual data entry or raw Odoo imports, these wizards validate data, report
errors clearly, and support a **dry-run** mode that previews what would happen
without committing changes.

## Dependencies

| Module | Reason |
|--------|--------|
| `sports_federation_base` | Clubs, teams |
| `sports_federation_people` | Players |
| `sports_federation_tournament` | Tournament participants |

## Wizards

### `federation.import.clubs.wizard`

Imports club records from a CSV file.

| Field | Type | Description |
|-------|------|-------------|
| `upload_file` | Binary | CSV file to import |
| `upload_filename` | Char | Filename |
| `dry_run` | Boolean | Preview mode (no commit) |
| `result_message` | Text | Import results summary |
| `line_count` / `success_count` / `error_count` | Integer | Statistics |

### `federation.import.players.wizard`

Imports player records from a CSV file with club linkage.

### `federation.import.teams.wizard`

Imports team records from a CSV file with club linkage.

### `federation.import.tournament.participants.wizard`

Imports tournament participant entries from a CSV file.

*All four wizards share the same field structure.*

## Key Behaviours

1. **Dry-run mode** — Toggle to preview import results without creating records.
2. **Validation** — Each row is validated; errors are reported per-line in
   `result_message`.
3. **Statistics** — After import, line/success/error counts show at a glance.
4. **Idempotent** — Existing records (matched by code/name) are updated rather than
   duplicated where possible.
