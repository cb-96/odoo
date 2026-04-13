# Sports Federation Import Tools

Wizard-driven CSV import for clubs, seasons, teams, players, and tournament
participants. The module is intended for federation onboarding and annual
rollover work where administrators need rehearsable imports instead of raw ORM
loads.

## Purpose

The import wizards provide a safer operator workflow than direct list-imports:

- dry-run rehearsal before any records are created
- approval checkpoints before live imports execute
- visible column mapping guidance in the wizard form
- code-first reference lookup where the target models expose stable codes
- categorized row-level failures instead of opaque batch errors
- duplicate-safe behavior that reports and skips existing records
- reusable template records that define the import contract per wizard
- governance-job verification summaries with before/after target counts
- managed partner contracts with token-authenticated subscriptions
- staged inbound deliveries that reuse the same governed preview and approval pipeline

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
- reusable `federation.import.template` selection
- checksum-bound `federation.import.job` approval workflow for live imports
- shared `dry_run`, `mapping_guide`, `result_message`, `line_count`,
  `success_count`, and `error_count` fields
- standardized error categories such as `missing_reference`,
  `duplicate_entry`, `format_error`, and `missing_required_field`

## Managed Partner Integrations

The module also provides a managed integration layer for machine-driven import
and export contracts.

Core models:

- `federation.integration.contract` defines the contract code, version,
  direction, transport, route hint, availability requirements, and optional
  linked import template.
- `federation.integration.partner` stores partner identity, token rotation, and
  delivery history.
- `federation.integration.partner.contract` records which contracts a partner is
  allowed to use.
- `federation.integration.delivery` stages inbound partner payloads and links
  them to the downstream governance job.

Managed integration behaviour:

1. Partners authenticate with `X-Federation-Partner-Code` and
   `X-Federation-Partner-Token`.
2. `/integration/v1/contracts` exposes the subscribed contract manifest,
   including database-specific availability and deprecation metadata.
3. Inbound payloads posted to `/integration/v1/inbound/<contract_code>/deliveries`
   are stored as staged deliveries with checksum-based duplicate reuse.
4. Operators open the staged delivery directly in the matching import wizard,
   review the preview, request approval, and then run the live import.
5. Delivery records mirror preview, approval, completion, and failure states so
   the inbound handoff remains auditable.

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

- `state`, `notes`, `target_club_count`, `target_team_count`,
  `target_tournament_count`, `target_participant_count`

Validation notes:

- dates must use `YYYY-MM-DD`
- state must be one of `draft`, `open`, `closed`, `cancelled`
- planning target columns must be whole numbers greater than or equal to zero

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
2. Live imports require an approved governance job tied to the current file checksum and template.
3. Real imports create valid rows and keep processing after row-level failures.
4. Existing records are not overwritten; duplicates are reported and skipped.
5. Result summaries include both totals and categorized error counts so
   administrators can fix the source CSV predictably.
6. Governance jobs store preview totals plus before/after record counts for post-import verification.
7. Staged partner deliveries can enter the same preview and approval workflow
  without bypassing governance controls.
