# Sports Federation Tournament

## Purpose
This module extends the sports federation base to manage tournaments, their stages, groups/poules, participants, and matches.

## Dependencies
- `sports_federation_base`

## Scope
- **Tournaments**: Single-day or multi-day events linked to a season with lifecycle management (Draft → Open → In Progress → Closed → Cancelled).
- **Tournament Stages**: Ordered phases within a tournament (Group Phase, Knockout, Final, Placement).
- **Tournament Groups / Poules**: Subdivisions within a stage for organizing participants.
- **Tournament Participants**: Teams registered in a tournament, optionally assigned to a stage and group.
- **Matches**: Individual games within a tournament, linked to a stage and optionally a group, with home/away teams and score tracking.

## Models
| Model | Chatter | Description |
|-------|---------|-------------|
| `federation.tournament` | ✓ | Tournament events |
| `federation.tournament.stage` | | Ordered stages within a tournament |
| `federation.tournament.group` | | Groups/poules within a stage |
| `federation.tournament.participant` | | Team registrations in a tournament |
| `federation.match` | ✓ | Individual match records |

## Menus
- Federation
  - Tournaments
    - Configuration
      - Stages
      - Groups
    - Participants
    - Matches