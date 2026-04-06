# Sports Federation Public Site

Public website pages for competitions, standings, and results. Makes tournament
information accessible to the general public without requiring authentication.

## Purpose

Extends the Odoo website module to publish competition pages. Fans,
club officials, and media can view tournament schedules, live standings, and
match results on public URLs without logging in.

## Dependencies

| Module | Reason |
|--------|--------|
| `website` | Odoo website framework |
| `sports_federation_tournament` | Tournaments, matches |
| `sports_federation_standings` | Standings data |
| `sports_federation_venues` | Venue information |
| `sports_federation_result_control` | Approved results |

## Models (inherited extensions)

### `federation.tournament` (extended)

| Field | Type | Description |
|-------|------|-------------|
| `website_published` | Boolean | Visible on public site |
| `public_description` | Html | Rich-text description for public |
| `public_slug` | Char | URL-friendly identifier |
| `show_public_results` | Boolean | Show results page |
| `show_public_standings` | Boolean | Show standings page |

### `federation.standing` (extended)

| Field | Type | Description |
|-------|------|-------------|
| `website_published` | Boolean | Visible on public site |
| `public_title` | Char | Display title for public |

## Controllers

### `PublicCompetitionsController`

| Route | Auth | Description |
|-------|------|-------------|
| `GET /competitions` | public | List all published tournaments |
| `GET /competitions/<tournament>` | public | Tournament detail page |
| `GET /competitions/<tournament>/standings` | public | Standings table |
| `GET /competitions/<tournament>/results` | public | Match results |
| `GET /competitions/<tournament>/schedule` | public | Upcoming fixtures |

## Key Behaviours

1. **Opt-in publishing** — Tournaments and standings must be explicitly published.
2. **Public access** — All routes use `auth="public"`, no login required.
3. **Slug-based URLs** — Clean URLs using `public_slug` field.
4. **Selective display** — Toggle results and standings visibility per tournament.
5. **Website templates** — QWeb templates for responsive public pages.
