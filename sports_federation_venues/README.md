# Sports Federation Venues

Venue, playing-area, and round scheduling support. Tracks physical locations
where matches are held, including address, capacity, facilities, individual
playing surfaces, and round-level venue assignment.

## Purpose

Centralises venue information so that tournaments, rounds, and matches can
reference structured location data rather than free-text fields. Playing areas
allow a single venue (e.g. a sports complex) to contain multiple usable
surfaces. Rounds now carry the shared schedule metadata for a block of matches:
the calendar date and venue live on the round, while each match keeps its own
exact kickoff time.

## Dependencies

| Module | Reason |
|--------|--------|
| `sports_federation_base` | Core entities |
| `sports_federation_tournament` | Tournaments and matches (extended) |

## Models

### `federation.venue`

A physical location (stadium, sports hall, complex).

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Venue name |
| `street` … `country_id` | Address | Full postal address |
| `contact_name` / `contact_email` / `contact_phone` | Char | On-site contact |
| `capacity` | Integer | Total spectator capacity |
| `equipment_notes` | Text | Available equipment |
| `playing_area_ids` | One2many | Courts, pitches, etc. |
| `playing_area_count` | Integer | Stat-button counter |
| `notes` | Text | General notes |
| `active` | Boolean | In use |

### `federation.playing.area`

A single playing surface within a venue.

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Area label (e.g. "Pitch 1") |
| `venue_id` | Many2one | Parent venue |
| `code` | Char | Short code |
| `capacity` | Integer | Surface-specific capacity |
| `surface_type` | Selection | grass / artificial / indoor / clay / other |
| `active` | Boolean | Available |
| `notes` | Text | Remarks |

### Inherited Extensions

- **`federation.tournament`** gains `venue_id` and `venue_notes` for tournament-wide
  venue planning notes.
- **`federation.tournament.stage`** surfaces its linked `round_ids` so stage admins
  can plan sequence, date, and venue directly on rounds.
- **`federation.tournament.round`** gains `venue_id`, complementing the base
  `round_date` field from the tournament module.
- **`federation.match`** gains `venue_id` and `playing_area_id`. When a match is
  linked to a round, the round becomes the authoritative shared venue/date scope.

## Key Behaviours

1. **Structured addresses** — Venues store full addresses with country reference.
2. **Multi-area venues** — A sports complex can have several pitches or courts.
3. **Round-owned schedule planning** — Administrators can create stage rounds up
  front and assign a date and venue to each one without duplicating scheduling
  concepts.
4. **Match ↔ Round consistency** — Assigning a round to a match propagates the
  tournament/stage scope, applies the round venue, and rejects conflicting venue
  or date combinations.
5. **Duplicate-pairing guardrails** — Teams in the same category cannot play the
  same opponent more than once inside the same round.
6. **Finance bridge integration** — When `sports_federation_finance_bridge` is installed,
  scheduling a match with a venue automatically creates or reuses a draft venue
  booking charge for passthrough settlement.
