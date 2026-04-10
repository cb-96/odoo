# Workflow: Public Publication

Publishing tournament information, standings, and results to the public website.

## Overview

The federation's public website allows fans, club officials, and media to view
competition information without logging in. This workflow covers how tournament
data is made publicly accessible through opt-in publication flags, publication identifiers,
and public page controllers.

## Modules Involved

| Module | Role |
|--------|------|
| `sports_federation_public_site` | Publication fields, website controllers, templates |
| `sports_federation_tournament` | Tournament and match data |
| `sports_federation_standings` | Standings data |
| `sports_federation_result_control` | Approved results |
| `sports_federation_notifications` | Publication emails to participating clubs/teams |
| `sports_federation_venues` | Venue information on match pages |
| `website` | Odoo website framework |

## Step-by-Step Flow

### 1. Tournament Preparation

**Actor**: Federation administrator
**Module**: `sports_federation_public_site`

Before publishing, ensure the tournament has:
1. A completed setup with stages, groups, and matches.
2. At least some matches completed with approved results.
3. Computed standings (for standings pages).

### 2. Publication Configuration

**Actor**: Federation administrator
**Module**: `sports_federation_public_site`

1. Open the tournament record.
2. Configure public-site fields:
   - `website_published` — Set to `True` to make visible.
   - `public_slug` — URL-friendly public identifier (e.g. `national-league-2025`). Keep it unique across tournaments.
   - `public_description` — Rich-text HTML description for the public page.
   - `show_public_results` — Toggle match results visibility.
   - `show_public_standings` — Toggle standings visibility.
3. When `website_published` changes from `False` to `True`, the notification
   dispatcher emails the participating club and team contacts so publication is
   visible outside the back office.

### 3. Standings Publication

**Actor**: Federation administrator
**Module**: `sports_federation_standings`

1. Ensure standings are computed and verified.
2. Set `website_published = True` on the standings record.
3. Optionally set `public_title` for display.

### 4. Public Pages Go Live

**Actor**: System (automatic)
**Module**: `sports_federation_public_site`

Once published, the following pages become available:

| URL | Content |
|-----|---------|
| `/competitions` | List of all published tournaments |
| `/competitions/<tournament>` | Tournament detail page with description |
| `/competitions/<tournament>/standings` | Standings table (if enabled) |
| `/competitions/<tournament>/results` | Match results (if enabled, only approved) |
| `/competitions/<tournament>/schedule` | Upcoming fixtures |

All routes use `auth="public"` — no login required.

### 5. Content Updates

**Actor**: Federation administrator

As the tournament progresses:
1. New match results are approved via the result pipeline.
2. Standings are recomputed and published.
3. Public pages automatically reflect the latest approved data.
4. Schedule pages show upcoming fixtures.
5. Publication emails are only sent on the publish transition itself; later
   content updates reuse the live public pages instead of re-emailing everyone.

### 6. End-of-Season

**Actor**: Federation administrator

1. After the tournament concludes, final standings and results remain published.
2. To remove from public view, set `website_published = False`.
3. Historical tournament pages can remain for archival purposes.

## Publication Checklist

| Item | Required | Module |
|------|----------|--------|
| Tournament exists with matches | Yes | `tournament` |
| Results approved | Yes (for results page) | `result_control` |
| Standings computed & published | Yes (for standings page) | `standings` |
| `website_published = True` on tournament | Yes | `public_site` |
| `public_slug` set and unique | Yes | `public_site` |
| `show_public_results` toggled | Optional | `public_site` |
| `show_public_standings` toggled | Optional | `public_site` |
| Standing records published | Yes (for standings page) | `standings` |

## Page Templates

The module provides QWeb website templates for:
- **Competition list** — Card/grid layout of published tournaments
- **Tournament detail** — Name, description, dates, and navigation
- **Standings table** — Ranked table with points, wins, draws, losses, goal stats
- **Results page** — Completed match list with scores
- **Schedule page** — Upcoming match list with dates and venues

All templates are responsive and follow Odoo website styling conventions.

## Access Control

| Access | Level |
|--------|-------|
| Public pages | No authentication required |
| Publication settings | Federation administrator only |
| Data changes | Only by backend users through standard modules |

Public pages are **read-only snapshots** of backend data. Visitors cannot modify
any data through the public site.

## Related Workflows

- [Tournament Lifecycle](WORKFLOW_TOURNAMENT_LIFECYCLE.md) — tournament must exist and have data
- [Result Pipeline](WORKFLOW_RESULT_PIPELINE.md) — results must be approved before publication
- [Season Registration](WORKFLOW_SEASON_REGISTRATION.md) — registered clubs appear in tournament pages
