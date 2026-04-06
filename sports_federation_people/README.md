# Sports Federation People

Player master data and license management for the federation. Tracks every
registered player's personal information, club affiliation, and maintains a
complete licensing history across seasons.

## Purpose

Provides the **player** and **player license** models that underpin roster
management, eligibility checks, discipline tracking, and compliance workflows.
Every module that deals with individual athletes depends on People.

## Dependencies

| Module | Reason |
|--------|--------|
| `sports_federation_base` | Clubs, teams, and seasons |

## Models

### `federation.player`

Master record for every registered individual. Names are split into first/last
for sorting and flexible display.

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char (computed) | `last_name, first_name` |
| `first_name` / `last_name` | Char | Legal name parts (both required) |
| `birth_date` | Date | Date of birth |
| `gender` | Selection | male / female / other |
| `nationality_id` | Many2one | Country of nationality |
| `club_id` | Many2one | Current club affiliation |
| `team_ids` | Many2many | Teams the player belongs to |
| `email` / `phone` / `mobile` | Char | Contact channels |
| `photo` | Binary | Player photograph |
| `state` | Selection | draft / active / suspended / retired |
| `license_ids` | One2many | Historical license records |
| `license_count` | Integer | Stat-button counter |
| `notes` | Text | Free-form notes |

- **State machine**: draft → active → suspended / retired.
- **Stat button** navigates to license history.

### `federation.player.license`

Season-scoped license that proves a player's right to compete. A player may hold
multiple licenses across seasons, but only one active license per season applies.

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Auto-generated license number (sequence) |
| `player_id` | Many2one | Licensed player |
| `season_id` | Many2one | Season the license covers |
| `club_id` | Many2one | Club at time of issue |
| `issue_date` / `expiry_date` | Date | Validity window |
| `state` | Selection | draft / active / expired / revoked |
| `category` | Selection | License category (e.g. amateur, professional) |
| `eligibility_notes` | Text | Eligibility remarks |
| `notes` | Text | Additional notes |

- License numbers generated via `ir.sequence`.

## Data Files

| File | Content |
|------|---------|
| `data/ir_sequence.xml` | `FED-LIC-` sequence for license numbers |
| `security/ir.model.access.csv` | CRUD rights for federation groups |

## Key Behaviours

1. **Name computation** — `name` is automatically composed from `last_name` and
   `first_name` and kept in sync.
2. **License numbering** — Every new license receives an auto-incremented
   `FED-LIC-XXXXX` reference via `ir.sequence`.
3. **Club ↔ Player link** — `club_id` on the player is the *current* affiliation;
   the license records preserve the historical club at time of issue.
