# Sports Federation Base

## Purpose
This module provides the foundation for the sports federation management system, covering clubs, teams, seasons, and season registrations.

## Dependencies
- `base`
- `mail`

## Scope
- **Federation Clubs**: Master data for clubs with contact information, addresses, and team relationships.
- **Federation Teams**: Teams belonging to clubs, classified by category (Senior, Youth, Junior, etc.) and gender.
- **Federation Seasons**: Time-bounded season periods with lifecycle management (Draft → Open → Closed → Cancelled).
- **Season Registrations**: Links a team to a season with a division/competition, using auto-generated references.
- **Security**: Two-level access control (User read-only, Manager full CRUD) under a "Sports Federation" category.
- **Sequences**: Auto-generated registration references with year-based prefix.

## Models
| Model | Chatter | Description |
|-------|---------|-------------|
| `federation.club` | ✓ | Clubs with teams |
| `federation.team` | ✓ (partial) | Teams belonging to clubs |
| `federation.season` | ✓ | Season periods |
| `federation.season.registration` | ✓ | Team-to-season mapping |

## Menus
- Federation
  - Master Data
    - Clubs
    - Teams
  - Seasons
  - Registrations