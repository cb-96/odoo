# Sports Federation Officiating

Referee management and match assignment tracking. Maintains a registry of
officials, their certifications, and automates the assignment workflow for matches.

## Purpose

Manages the **referee lifecycle** separately from the club/team hierarchy. Referees
operate across tournaments and are assigned to specific matches in defined roles
(head referee, assistant, etc.).

## Dependencies

| Module | Reason |
|--------|--------|
| `sports_federation_base` | Core entities |
| `sports_federation_tournament` | Matches |
| `sports_federation_people` | Person concept reference |

## Models

### `federation.referee`

Master record for each registered official.

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Full name |
| `email` / `phone` / `mobile` | Char | Contact channels |
| `certification_level` | Selection | national / regional / local / trainee |
| `active` | Boolean | Active in the registry |
| `certification_ids` | One2many | Certification history |
| `match_assignment_ids` | One2many | Match assignments |
| `certification_count` / `assignment_count` | Integer | Stat-button counters |
| `notes` | Text | Free-form notes |

### `federation.referee.certification`

A specific certification held by a referee, with validity tracking.

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Certificate title |
| `referee_id` | Many2one | Referee |
| `level` | Selection | national / regional / local / trainee |
| `issue_date` / `expiry_date` | Date | Validity window |
| `issuing_body` | Char | Certification authority |
| `active` | Boolean | Currently valid |
| `notes` | Text | Remarks |

### `federation.match.referee`

Links a referee to a match in a specific role.

| Field | Type | Description |
|-------|------|-------------|
| `match_id` | Many2one | The match |
| `referee_id` | Many2one | The official |
| `tournament_id` | Many2one | Computed from match |
| `role` | Selection | head / assistant / fourth / var |
| `state` | Selection | assigned / confirmed / completed / cancelled |
| `notes` | Text | Assignment notes |

- **SQL constraint**: unique (match_id, referee_id, role) — prevents duplicate
  role assignments.

## Key Behaviours

1. **Certification tracking** — Expiry dates allow monitoring whether officials
   meet current requirements.
2. **Role-based assignment** — Each match can have multiple referees in distinct
   roles.
3. **Assignment state machine** — assigned → confirmed → completed / cancelled.
4. **Tournament context** — Assignments carry a computed tournament reference for
   filtering and reporting.
