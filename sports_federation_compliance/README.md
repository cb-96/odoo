# Sports Federation Compliance

Document requirements, submissions, and compliance checking. Ensures that clubs,
players, referees, and venues maintain all required documentation (licences,
insurance certificates, safety reports, etc.).

## Purpose

Defines what **documents are required** for each entity type, tracks
**submissions** of those documents with attachments and expiry dates, and runs
**compliance checks** to flag missing or expired documentation.

## Dependencies

| Module | Reason |
|--------|--------|
| `sports_federation_base` | Clubs |
| `sports_federation_people` | Players |
| `sports_federation_officiating` | Referees |
| `sports_federation_venues` | Venues |
| `sports_federation_portal` | Club representatives |
| `mail` | Chatter |

## Models

### `federation.document.requirement`

A type of document that certain entities must provide.

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Requirement title |
| `code` | Char | Unique code |
| `target_model` | Selection | Which entity type (club / player / referee / venue / club_representative) |
| `required_for_all` | Boolean | Applies to all entities of this type |
| `requires_expiry_date` | Boolean | Submission must include an expiry date |
| `validity_days` | Integer | Default validity period |
| `description` | Text | Detailed requirements |
| `active` | Boolean | Currently enforced |

### `federation.document.submission`

An actual document submitted against a requirement.

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Submission title |
| `requirement_id` | Many2one | Which requirement this fulfils |
| `target_model` | Selection (computed) | From requirement |
| `club_id` / `player_id` / `referee_id` / `venue_id` / `club_representative_id` | Many2one | Target entity |
| `status` | Selection | draft / submitted / approved / rejected / replacement_requested / expired |
| `attachment_ids` | Many2many | Uploaded files |
| `issue_date` / `expiry_date` | Date | Document validity |
| `reviewer_id` | Many2one | Who reviewed |
| `reviewed_on` | Datetime | Review timestamp |
| `is_expired` | Boolean (computed) | True if expiry_date < today |
| `target_display` | Char (computed) | Readable target entity name |
| `notes` | Text | Remarks |

- **State machine**: draft → submitted → approved / rejected / replacement_requested → expired.
- **Constraint**: exactly one target entity field must be set.
- **Expired ribbon** shown in form view when document has passed its expiry date.

### `federation.compliance.check`

A check result linking a requirement to an entity's submission status.

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Check title |
| `target_model` | Selection | Entity type |
| `club_id` / `player_id` / `referee_id` / `venue_id` / `club_representative_id` | Many2one | Target |
| `status` | Selection | compliant / missing / pending / expired |
| `requirement_id` | Many2one | Which requirement |
| `submission_id` | Many2one | Linked submission (if any) |
| `checked_on` | Datetime | When the check ran |
| `note` | Char | Result note |
| `target_display` | Char (computed) | Readable target name |

### `federation.compliance.check.archive`

Immutable history row capturing how a compliance check looked at a point in
time.

| Field | Type | Description |
|-------|------|-------------|
| `compliance_check_id` | Many2one | Source compliance check |
| `archived_on` / `checked_on` | Datetime | Archive timestamp and source check timestamp |
| `target_model` / `target_res_id` | Char / Integer | Archived target reference |
| `requirement_id` / `submission_id` | Many2one | Requirement and linked submission snapshot |
| `status` | Selection | Archived compliance status |
| `note` | Char | Archived operator note |

## Key Behaviours

1. **Requirement definition** — Federation defines which documents each entity type
   must provide.
2. **Submission workflow** — Documents are uploaded, submitted, and reviewed with
   approval/rejection.
3. **Expiry tracking** — Computed `is_expired` field auto-flags overdue documents.
4. **Compliance checks** — Programmatic checks produce compliant / missing / pending /
   expired statuses per entity.
5. **Multi-entity support** — Same framework covers clubs, players, referees, venues,
   and club representatives.
6. **Portal self-service workspace** — Scoped portal users can review their own
    requirements, renewal deadlines, remediation notes, and submission history at
    `/my/compliance`.
7. **Portal submission flow** — Club representatives and referees can upload
    replacement documents and submit renewals directly from the portal detail page
    without backend access.
   The controller hands the write to
   `federation.document.submission._portal_submit_submission()` so attachment
   creation and submission state changes stay inside the model boundary.
8. **Historical evidence** — compliance checks now append archive rows on create
   and on tracked status changes so operators can review how a target moved from
   missing to compliant over time.

## Portal Self-Service

Portal routes:

- `GET /my/compliance` — workspace listing with renewal warnings, review state,
   and attention-first sorting
- `GET /my/compliance/<requirement_id>/<target_model>/<target_id>` — detail page
   for one requirement and target record
- `POST /my/compliance/<requirement_id>/<target_model>/<target_id>/submit` —
   attachment-backed submission or renewal request

Portal workspace behaviour:

- access is limited to targets the current portal user is allowed to manage
- remediation notes from the reporting layer are surfaced when available
- renewal windows are highlighted before expiry so replacement documents can be
   submitted proactively
- attachment creation preserves the portal user identity while still using
   controlled elevated writes for the compliance models through
   `_portal_submit_submission()` and `_portal_create_submission_attachments()`
