# Sports Federation Venues

Venue and playing-area management. Tracks physical locations where matches are
held, including address, capacity, facilities, and individual playing surfaces.

## Purpose

Centralises venue information so that tournaments and matches can reference
structured location data rather than free-text fields. Playing areas allow a single
venue (e.g. a sports complex) to contain multiple usable surfaces.

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

- **`federation.tournament`** gains a `venues` Many2many field.
- **`federation.match`** gains a `venue_id` Many2one field, replacing the plain
  text `venue` field with a structured reference.

## Key Behaviours

1. **Structured addresses** — Venues store full addresses with country reference.
2. **Multi-area venues** — A sports complex can have several pitches or courts.
3. **Tournament ↔ Venue link** — Tournaments declare which venues are available;
   matches reference specific venues.
4. **Finance bridge integration** — When `sports_federation_finance_bridge` is installed,
  scheduling a match with a venue automatically creates or reuses a draft venue
  booking charge for passthrough settlement.
