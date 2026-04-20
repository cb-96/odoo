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
The transient import models now live under the standard `wizards/` package to
match the rest of the repository.

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
- shared `_execute_row_create(...)` handling so live imports reuse one
  row-create failure path instead of ad hoc wizard-level try/except blocks
- standardized error categories such as `missing_reference`,
  `duplicate_entry`, `format_error`, and `missing_required_field`
- explicit compatibility handling for legacy CSV aliases tracked in
  `COMPATIBILITY_INVENTORY.md`

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

Current model layout:

- `models/integration_contract.py` keeps contract manifest and availability rules.
- `models/integration_partner.py` keeps partner identity, subscription lookup,
  and the stable authentication entry point.
- `models/integration_partner_token_mixin.py` keeps token generation, hashing,
  verification, migration, and hashed persistence hooks.
- `models/integration_partner_rotation_mixin.py` keeps manager-driven token
  rotation and audit logging.
- `models/integration_partner_contract.py` keeps subscription state and usage tracking.
- `models/integration_delivery.py` keeps the ORM fields and composes focused helper mixins.
- `models/integration_delivery_stage_mixin.py` keeps inbound staging, idempotency,
  duplicate reuse, and attachment creation.
- `models/integration_delivery_workflow_mixin.py` keeps wizard handoff and delivery
  state transitions.
- `models/integration_delivery_retention_mixin.py` keeps retention cleanup.

Current wizard layout:

- `wizards/import_wizard_mixin.py` remains the stable shared surface used by all
  import wizards.
- `wizards/import_wizard_csv_mixin.py` keeps CSV parsing, column validation,
  row helpers, and shared error taxonomy.
- `wizards/import_wizard_governance_mixin.py` keeps approval checks,
  governance-job persistence, and result finalization.

Current controller layout:

- `controllers/integration_api.py` keeps the stable public route surface and
  route-level orchestration.
- `controllers/integration_api_auth_mixin.py` keeps header parsing, partner
  authentication, caller identity, and rate-limit subject helpers.
- `controllers/integration_api_response_mixin.py` keeps JSON response shaping
  and typed error payload helpers.

Phased maintainability plan:

1. Phase 1 completed: the former multi-model gateway hotspot was split into
  per-model files without changing model names, fields, or table ownership.
  Test impact: existing import-tools tests should stay green. Migration risk:
  none, because this is a file-layout change only.
2. Phase 2 completed: delivery staging, idempotency, workflow handoff, and
  retention cleanup now live in dedicated helper mixins while
  `federation.integration.delivery` keeps the ORM contract stable. Test impact:
  inbound delivery staging, idempotency, and retention coverage stays green.
  Migration risk: replay semantics and attachment linkage.
3. Phase 3 completed: token generation, hashing, verification, migration, and
  rotation/audit helpers now live in dedicated partner mixins while
  `federation.integration.partner` keeps the stable ORM entry points for
  authentication and subscription lookup. Test impact: token rotation and
  legacy-token migration coverage stay green. Migration risk: stored hash
  compatibility and audit logging.
4. Phase 4 completed: `wizards/import_wizard_mixin.py` now composes dedicated
  CSV and governance/result helper mixins while preserving the shared wizard
  API. Test impact: shared mixin coverage plus wizard-specific dry-run and
  live-import flows stay green. Migration risk: approval checksum binding and
  result-summary compatibility.
5. Phase 5 completed: `controllers/integration_api.py` now composes dedicated
  auth and response helper mixins while preserving the public route surface and
  existing headers/status codes. Test impact: integration API credential,
  rate-limit, finance export, and inbound delivery coverage stays green.
  Migration risk: request patching in tests and route-level error semantics.

Managed integration behaviour:

1. Partners authenticate with `X-Federation-Partner-Code` plus either
  `X-Federation-Partner-Token` or `Authorization: Bearer <token>`.
2. `/integration/v1/contracts` exposes the subscribed contract manifest,
   including database-specific availability and deprecation metadata.
3. Inbound payloads posted to `/integration/v1/inbound/<contract_code>/deliveries`
  are stored as staged deliveries with checksum-based duplicate reuse and can
  optionally bind an `X-Federation-Idempotency-Key` for safe retries.
4. Operators open the staged delivery directly in the matching import wizard,
   review the preview, request approval, and then run the live import.
5. Delivery records mirror preview, approval, completion, and failure states so
   the inbound handoff remains auditable.

Managed integration contract docs:

- narrative policy and deprecation guidance live in `INTEGRATION_CONTRACTS.md`
- machine-readable route and payload definitions live in `openapi/integration_v1.yaml`

Credential handling:

- partner secrets are stored hashed at rest; the raw token is never shown again after issuance
- federation managers issue or rotate a token from the partner form, then copy it from the one-time modal
- each manager-driven token rotation writes a shared audit event that appears in `Reporting > Token Rotation Audit`
- URL query parameters are rejected for partner authentication to avoid leaking secrets into logs, browser history, or proxy traces
- legacy plaintext tokens are migrated into hashed storage on module load and flagged for mandatory rotation

Inbound delivery guardrails:

- partner uploads must use a `.csv` filename and a `text/csv` content type when declared
- inbound payloads larger than 5 MiB are rejected before staging
- duplicate inbound payloads are deduplicated by checksum before a new delivery record or attachment is created
- explicit inbound idempotency keys replay the original delivery across retries and reject conflicting payload reuse
- successful inbound API responses now expose `delivery_outcome` plus `X-Federation-Delivery-Outcome` so clients can distinguish fresh staging from checksum reuse and idempotent replay
- terminal inbound deliveries are purged automatically once they exceed the retention windows documented in `DATA_RETENTION_POLICY.md`; the staged payload attachment is deleted with the delivery record

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
8. Delivery failures and partial-import outcomes surface in the reporting
  operator checklist so inbound issues are visible before partners report them.
