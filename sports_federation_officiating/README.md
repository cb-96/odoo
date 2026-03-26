# Sports Federation Officiating

## Purpose
Referee management and match assignments for the sports federation.

## Dependencies
- `sports_federation_base`
- `sports_federation_tournament`
- `sports_federation_people`

## Scope
- **Referees**: Master data with contact details, certification level, and availability
- **Referee Certifications**: Historical record of certifications with levels and validity dates
- **Match Assignments**: Assign referees to matches with roles (head, assistant, fourth official, table)

## Models
| Model | Chatter | Description |
|-------|---------|-------------|
| `federation.referee` | ✓ | Referee profiles |
| `federation.referee.certification` | | Certification history |
| `federation.match.referee` | | Match assignments with roles |

## Menus
- Federation > Officiating > Referees
- Federation > Officiating > Configuration > Certifications
- Federation > Officiating > Match Assignments