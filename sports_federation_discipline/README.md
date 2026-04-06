# Sports Federation Discipline

Incident reporting, disciplinary case management, sanctions, and player
suspensions. Provides the full disciplinary pipeline from incident detection
through case resolution to sanction enforcement.

## Purpose

Tracks **incidents** that occur during matches, groups them into **disciplinary
cases** for investigation, and records **sanctions** (fines, warnings) and
**suspensions** (match bans) as outcomes. Links back to players, clubs, and
referees for comprehensive disciplinary records.

## Dependencies

| Module | Reason |
|--------|--------|
| `sports_federation_base` | Clubs |
| `sports_federation_people` | Players |
| `sports_federation_tournament` | Matches |
| `mail` | Chatter |

## Models

### `federation.match.incident`

An event that occurred during a match that may trigger disciplinary action.

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Incident title |
| `match_id` | Many2one | The match |
| `player_id` | Many2one | Involved player |
| `club_id` | Many2one | Involved club |
| `referee_id` | Many2one | Reporting referee |
| `incident_type` | Selection | yellow_card / red_card / misconduct / violence / other |
| `minute_text` | Char | Match minute (text for flexibility) |
| `description` | Text | What happened |
| `case_id` | Many2one | Linked disciplinary case |
| `date_reported` | Date | When reported |
| `reported_by_user_id` | Many2one | System user who filed it |
| `status` | Selection | reported / under_review / resolved / dismissed |

### `federation.disciplinary.case`

An investigation triggered by one or more incidents.

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Case title |
| `reference` | Char | Auto-sequence reference number |
| `state` | Selection | open / investigation / decided / closed |
| `opened_on` / `decided_on` / `closed_on` | Date | Timeline |
| `responsible_user_id` | Many2one | Case handler |
| `incident_ids` | One2many | Related incidents |
| `sanction_ids` | One2many | Resulting sanctions |
| `suspension_ids` | One2many | Resulting suspensions |
| `subject_player_id` / `subject_club_id` / `subject_referee_id` | Many2one | Subject |
| `summary` / `notes` | Text | Case details |

- **State machine**: open → investigation → decided → closed.
- **Auto-numbering** via `ir.sequence`.

### `federation.sanction`

A penalty imposed as the outcome of a disciplinary case.

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Sanction title |
| `case_id` | Many2one | Parent case |
| `sanction_type` | Selection | fine / warning / ban / point_deduction / other |
| `player_id` / `club_id` / `referee_id` | Many2one | Who is sanctioned |
| `amount` / `currency_id` | Monetary | For fines |
| `effective_date` | Date | When it takes effect |
| `notes` | Text | Details |

### `federation.suspension`

A time-bound match ban for a player.

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Suspension title |
| `case_id` | Many2one | Parent case |
| `player_id` | Many2one | Suspended player |
| `date_start` / `date_end` | Date | Ban period |
| `state` | Selection | active / served / overturned |
| `notes` | Text | Details |

## Security Groups

| Group | Purpose |
|-------|---------|
| Disciplinary Staff | Can manage incidents, cases, sanctions, and suspensions |

## Data Files

| File | Content |
|------|---------|
| `data/ir_sequence.xml` | `FED-DISC-` sequence for case reference numbers |

## Key Behaviours

1. **Incident → Case linking** — Incidents can be grouped into a case for joint handling.
2. **Case lifecycle** — open → investigation → decided → closed with date tracking.
3. **Multiple outcomes** — A single case can produce multiple sanctions and suspensions.
4. **Player integration** — Inherited views add discipline tabs to player forms.
5. **Match integration** — Inherited views add incident lists to match forms.
