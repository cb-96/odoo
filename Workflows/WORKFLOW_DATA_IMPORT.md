# Workflow: Data Import

Bulk data loading via CSV import wizards with validation, dry-run preview, and
error reporting.

## Overview

During initial federation setup or season transitions, large amounts of data need
to be loaded — club lists, player registrations, team rosters, and tournament
participants. The import tools module provides guided wizards that validate data
before committing, support a dry-run mode, and report errors per row.

## Modules Involved

| Module | Role |
|--------|------|
| `sports_federation_import_tools` | All four import wizards |
| `sports_federation_base` | Target for club and team imports |
| `sports_federation_people` | Target for player imports |
| `sports_federation_tournament` | Target for tournament participant imports |

## Available Import Wizards

| Wizard | Target Model | CSV Fields |
|--------|-------------|------------|
| Import Clubs | `federation.club` | name, code, city, etc. |
| Import Teams | `federation.team` | name, code, club reference |
| Import Players | `federation.player` | first_name, last_name, birth_date, club reference |
| Import Tournament Participants | `federation.tournament.participant` | team reference, tournament reference, seed |

## Step-by-Step Flow

### 1. CSV Preparation

**Actor**: Federation administrator
**Format Requirements**:

1. Prepare a UTF-8 CSV file (no BOM) with headers matching expected field names.
2. Use semicolons or commas as delimiters (wizard auto-detects).
3. Reference existing records by code or name (e.g. club code for team→club link).
4. Include all required fields; optional fields can be left blank.

### 2. Wizard Launch

**Actor**: Federation administrator
**Module**: `sports_federation_import_tools`

1. Navigate to **Federation → Import Tools → Import [Entity]**.
2. Open the appropriate wizard form.
3. Upload the CSV file via the `upload_file` Binary field.

### 3. Dry-Run Preview

**Actor**: Federation administrator
**Module**: `sports_federation_import_tools`

1. Check the **Dry Run** checkbox.
2. Click **Import**.
3. The wizard processes every row:
   - Validates required fields
   - Checks references (e.g. does the club code exist?)
   - Detects duplicates
4. Results are displayed in the `result_message` field:
   - Per-row status (success / error with reason)
   - Summary statistics: `line_count`, `success_count`, `error_count`
5. **No records are created** in dry-run mode — it's a pure validation pass.

### 4. Error Correction

**Actor**: Federation administrator

1. Review errors from the dry-run output.
2. Fix the CSV file:
   - Correct invalid references
   - Fill in missing required fields
   - Remove duplicate entries
3. Re-upload and re-run dry-run until `error_count = 0`.

### 5. Commit Import

**Actor**: Federation administrator
**Module**: `sports_federation_import_tools`

1. Uncheck the **Dry Run** checkbox.
2. Click **Import**.
3. The wizard creates (or updates) records for each valid row.
4. Existing records matched by code/name are updated rather than duplicated.
5. Final statistics confirm the import outcome.

### 6. Post-Import Verification

**Actor**: Federation administrator

1. Navigate to the target list view (clubs, teams, players, participants).
2. Verify imported records appear correctly.
3. Check linked references (e.g. players have correct club assignments).
4. Run compliance checks if applicable.

## Process Diagram

```
                    ┌─────────┐
                    │ Prepare │
                    │   CSV   │
                    └────┬────┘
                         │
                    ┌────▼────┐
                    │ Upload  │
                    │  File   │
                    └────┬────┘
                         │
                  ┌──────▼──────┐
               ┌──┤  Dry Run?   ├──┐
               │  └─────────────┘  │
              Yes                  No
               │                   │
        ┌──────▼──────┐    ┌──────▼──────┐
        │  Validate   │    │   Create    │
        │  (preview)  │    │  Records    │
        └──────┬──────┘    └──────┬──────┘
               │                   │
        ┌──────▼──────┐    ┌──────▼──────┐
        │  Errors?    │    │   Review    │
        │  Fix CSV    │    │  Results    │
        └──────┬──────┘    └─────────────┘
               │
          (loop back)
```

## Field Mappings

### Clubs CSV

| Column | Maps To | Required |
|--------|---------|----------|
| `name` | `federation.club.name` | Yes |
| `code` | `federation.club.code` | Yes (unique) |
| `city` | `federation.club.city` | No |
| ... | Other club fields | No |

### Players CSV

| Column | Maps To | Required |
|--------|---------|----------|
| `first_name` | `federation.player.first_name` | Yes |
| `last_name` | `federation.player.last_name` | Yes |
| `birth_date` | `federation.player.birth_date` | No |
| `club_code` | Lookup → `federation.club` | No |
| ... | Other player fields | No |

### Teams CSV

| Column | Maps To | Required |
|--------|---------|----------|
| `name` | `federation.team.name` | Yes |
| `code` | `federation.team.code` | Yes |
| `club_code` | Lookup → `federation.club` | Yes |

### Tournament Participants CSV

| Column | Maps To | Required |
|--------|---------|----------|
| `team_code` | Lookup → `federation.team` | Yes |
| `tournament_code` | Lookup → `federation.tournament` | Yes |
| `seed` | `federation.tournament.participant.seed` | No |

## Key Behaviours

1. **Idempotent** — Running the same import twice updates existing records rather
   than creating duplicates (matched by code or unique key).
2. **Transactional** — If the wizard is cancelled mid-way, no partial data is saved.
3. **BOM handling** — UTF-8 BOM characters are stripped automatically.
4. **Error isolation** — One bad row doesn't prevent other rows from importing.

## Related Workflows

- [Season Registration](WORKFLOW_SEASON_REGISTRATION.md) — imported clubs feed into registration
- [Tournament Lifecycle](WORKFLOW_TOURNAMENT_LIFECYCLE.md) — imported participants feed into tournaments
