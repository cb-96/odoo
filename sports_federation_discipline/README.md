# Sports Federation Discipline

## Purpose
Incidents, cases, sanctions, and suspensions management

## Dependencies
- `sports_federation_base`
- `sports_federation_people`
- `sports_federation_tournament`
- `mail`

## Models
| Model | Chatter | Description |
|-------|---------|-------------|
| `federation.match.incident` |  | Match Incident |
| `federation.disciplinary.case` | ✓ | Disciplinary Case |
| `federation.sanction` |  | Sanction |
| `federation.suspension` |  | Suspension |

## Menus
- Federation
  - Discipline
    - Discipline
      - Incidents
      - Cases
      - Sanctions
      - Suspensions