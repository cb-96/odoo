# Sports Federation People

## Purpose
Player master data and license management for the sports federation.

## Dependencies
- `sports_federation_base`

## Scope
- **Players**: Master data with personal info, club affiliation, team membership, federation status
- **Player Licenses**: Season-based licenses with issue/expiry dates, category, eligibility notes

## Models
| Model | Chatter | Description |
|-------|---------|-------------|
| `federation.player` | ✓ | Player profiles |
| `federation.player.license` | | Season-based licenses |

## Menus
- Federation > People > Players
- Federation > People > Configuration > Licenses