# Sports Federation Module Architecture - Technical Note

## Module Split Summary

| Module | Depends On | Models | Purpose |
|--------|-----------|--------|---------|
| `sports_federation_base` | `base`, `mail` | federation.club, federation.team, federation.season, federation.season.registration | Master data: clubs, teams, seasons, registrations |
| `sports_federation_tournament` | `sports_federation_base` | federation.tournament, federation.tournament.stage, federation.tournament.group, federation.tournament.participant, federation.match | Tournament management: events, stages, groups, participants, matches |
| `sports_federation_competition_engine` | `sports_federation_tournament` | (none) | Service scaffold: schedule generation, standings, knockout brackets |

## What Moved Where

- **Clubs and Teams** → `sports_federation_base`: These are foundational entities that other modules reference.
- **Seasons and Registrations** → `sports_federation_base`: Season lifecycle and team-to-season mapping belong at the base level.
- **Tournaments** → `sports_federation_tournament`: Tournament events depend on seasons from the base module.
- **Stages and Groups** → `sports_federation_tournament`: Structural subdivisions of tournaments.
- **Participants** → `sports_federation_tournament`: Teams registered in tournaments.
- **Matches** → `sports_federation_tournament`: Individual games within tournaments.
- **Competition Engine** → `sports_federation_competition_engine`: Pure service logic with no models, ready for future wizards and computed fields.

## Why This Split Is Future-Proof

1. **Single Responsibility**: Each module has a clear, focused scope. The base module handles master data, the tournament module handles event structure, and the engine module handles algorithms.

2. **Minimal Coupling**: The tournament module only depends on base for team/club references. The engine module only depends on tournament for data access.

3. **Extension-Friendly**: The engine module is intentionally empty. Adding schedule generation wizards, standings views, or automatic fixtures does not require modifying the base or tournament modules.

4. **Security Isolation**: Security groups are defined in the base module and referenced by the tournament module. New modules can extend ACLs without touching existing ones.

5. **Independent Installation**: The base module can be installed without tournaments. Tournaments can be installed without the engine. This allows partial adoption.

## Extension Points for Next Steps

### Competition Engine (Immediate)
- Implement `generate_round_robin_schedule()` with proper pairing algorithms
- Implement `generate_standings()` with points/goal-difference sorting
- Implement `generate_knockout_bracket()` with seeding and bye handling
- Add a wizard model (`federation.schedule.wizard`) for user-facing schedule generation

### Tournament Enhancements (Near-term)
- Add `federation.tournament.standings` computed model or view
- Add `federation.match.lineup` model for team rosters per match
- Add `federation.match.event` model for goals, cards, substitutions
- Add calendar view for match scheduling

### Base Module Enhancements (Near-term)
- Add `federation.club.official` model for club contacts
- Add `federation.team.player` model for player rosters
- Add `federation.division` model as a formal entity (instead of a Char field on registrations)
- Add import/export wizards for bulk club and team data

### Reporting (Later)
- Add `federation.report.standings` QWeb report
- Add `federation.report.match.sheet` QWeb report
- Add dashboard views with KPIs (active clubs, registered teams, upcoming matches)

### Integration (Later)
- Add `federation.website` module for public-facing tournament pages
- Add `federation.live.scoring` module for real-time match updates
- Add calendar integration for match scheduling