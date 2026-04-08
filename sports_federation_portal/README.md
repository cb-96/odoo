# Sports Federation Portal

## Solution Design

### Overview
The `sports_federation_portal` module adds public website pages and portal flows for club representatives to register for tournaments and seasons. It sits on top of `sports_federation_base` and `sports_federation_tournament`, using `website` and `portal` from Odoo core.

### Key Design Decisions

#### 1. Ownership Mapping Strategy

**Club Representative Model (`federation.club.representative`)**

A dedicated model links `res.users` to `federation.club` records. This is the single source of truth for "which portal user owns which club."

- One user can represent multiple clubs (rare but supported).
- One club can have multiple representatives (primary + secondary).
- Controllers use `_get_clubs_for_user()` to resolve ownership before every operation.

**Why a dedicated model instead of a Many2many on `res.users`?**
- Keeps the portal layer cleanly separated from the base module.
- Allows adding role, active flag, and audit fields without touching `federation.club`.
- Record rules can reference `user.representative_ids.mapped('club_id')` directly.

#### 2. Tournament Registration Model (`federation.tournament.registration`)

A new intermediate model captures portal-side registration requests with a full workflow:

```
draft -> submitted -> confirmed / rejected / cancelled
```

**Why not reuse `federation.tournament.participant` directly?**
- `federation.tournament.participant` is a backend-managed record. It should only be created after federation staff reviews the request.
- The registration model adds a review step, rejection reason, and links back to the submitting user.
- On confirmation, the system auto-creates a `federation.tournament.participant` record.

#### 3. Season Registration Extension

The existing `federation.season.registration` model is extended with a `submitted` state and portal fields (`user_id`, `partner_id`, `rejection_reason`). This avoids creating a duplicate model while adding the portal workflow.

#### 4. Public vs Portal Separation

| Layer | Auth | Access |
|-------|------|--------|
| Public (`/tournaments`, `/tournament/<id>`) | `auth="public"` | Anyone can view open/in-progress/closed tournaments. Read-only. Uses `sudo()`. |
| Registration form (`/tournament/<id>/register`) | `auth="user"` | Logged-in users only. Ownership verified server-side. |
| Portal (`/my/*`) | `auth="user"` | Only records belonging to user's club. Record rules enforce this. |

#### 5. Record Rule Strategy

Portal users (`group_federation_portal_club`) get these record rules:

| Model | Rule | Effect |
|-------|------|--------|
| `federation.club.representative` | `('user_id', '=', user.id)` | See only own representative records |
| `federation.club` | `('id', 'in', user.representative_ids.mapped('club_id').ids)` | See only own clubs |
| `federation.team` | `('club_id', 'in', ...)` | See only own teams |
| `federation.season.registration` | `('club_id', 'in', ...)` | See only own season registrations |
| `federation.tournament.registration` | `('club_id', 'in', ...)` | See only own tournament registrations |
| `federation.tournament` | `[(1, '=', 1)]` | See all tournaments (read-only, for listing) |
| `federation.tournament.participant` | `('club_id', 'in', ...)` | See only own participants |

Additionally, controllers validate ownership on every write operation as defense-in-depth.

## Module Tree

```
sports_federation_portal/
    __init__.py
    __manifest__.py
    controllers/
        __init__.py
        main.py
    data/
        ir_sequence.xml
    models/
        __init__.py
        federation_club.py
        federation_club_representative.py
        federation_season_registration.py
        federation_tournament_registration.py
    security/
        ir.model.access.csv
        ir_rule.xml
        res_groups.xml
    views/
        federation_club_representative_views.xml
        federation_tournament_registration_views.xml
        portal_templates.xml
        website_menus.xml
        website_tournament_templates.xml
```

## Security Explanation

### Groups
- **`group_federation_portal_club`**: Portal Club Representative. Implies `base.group_portal`. Users in this group get ACL and record rules that restrict them to their club's data.

### ACL (Access Control List)
Portal group gets:
- **Read** on clubs, teams, seasons, tournaments, participants (for display).
- **Read/Create/Write** on season registrations and tournament registrations (to submit and cancel).
- **Read-only** on club representatives (to resolve ownership).
- **No unlink** on anything (portal users cannot delete records).

Manager group gets full CRUD on all new models.

### Record Rules
Seven record rules ensure portal users can only access data belonging to their clubs. The domain `('club_id', 'in', user.representative_ids.mapped('club_id').ids)` is used consistently.

### Controller-Level Validation
Every write operation in the controllers:
1. Resolves the user's clubs via `_get_clubs_for_user()`.
2. Verifies the target team/registration belongs to those clubs.
3. Checks for duplicates and capacity limits.
4. Creates records with `sudo()` after validation passes.

### Public Routes
Public routes use `sudo()` to bypass ACL (since anonymous users have no federation access). They only expose:
- Tournament name, dates, location, status, participant count.
- No sensitive internal data (no email, phone, notes from clubs, etc.).

## Verification Checklist

### Security Flows
- [ ] **Public user cannot access `/my/club`** - Should redirect to login.
- [ ] **Portal user without representative record sees "not assigned" message** on `/my/club`.
- [ ] **Portal user A cannot see portal user B's registrations** - Record rules prevent this.
- [ ] **Portal user cannot register a team from another club** - Controller validates `team.club_id in clubs`.
- [ ] **Portal user cannot cancel a registration from another club** - Controller checks ownership.
- [ ] **Anonymous user cannot POST to `/tournament/<id>/register`** - `auth="user"` blocks it.
- [ ] **CSRF tokens are required on all POST forms** - All forms include `csrf_token`.

### Functional Flows
- [ ] **Tournament listing** (`/tournaments`) shows open/in_progress/closed tournaments.
- [ ] **Tournament detail** (`/tournament/<id>`) shows participants and register button when state is `open`.
- [ ] **Tournament registration** creates a `federation.tournament.registration` in `submitted` state.
- [ ] **Duplicate registration** is rejected with an error message.
- [ ] **Max participants** limit is enforced.
- [ ] **Season registration** creates a `federation.season.registration` in `submitted` state.
- [ ] **Cancel registration** sets state to `cancelled`.
- [ ] **Confirm registration** in backend creates `federation.tournament.participant`.
- [ ] **Portal dashboard** shows federation cards for club representatives.
- [ ] **Breadcrumb navigation** works on all pages.

### Backend Flows
- [ ] **Tournament registration form** shows statusbar, buttons, and chatter.
- [ ] **Tournament registration form** explains why teams are unavailable in backend dropdowns.
- [ ] **Submit/Confirm/Reject/Cancel** buttons work with correct visibility.
- [ ] **Club representative** can be created from club form view.
- [ ] **Menu items** appear under Federation > Portal.
- [ ] **Search/filters** work on tournament registration tree view.

## Live Browser Verification

Use this procedure when you need to validate the real website flow against the running Docker stack instead of only relying on tests.

### 1. Seed deterministic portal data

Create or update a small set of records through Odoo shell so the browser check is repeatable.

```bash
docker compose exec odoo odoo shell -c /etc/odoo/odoo.conf -d odoo
```

Recommended dataset:
- one club with a representative user
- one open tournament with explicit `category` and `gender`
- one eligible team for that tournament
- one ineligible team for that tournament

Important details:
- use `group_ids` on `res.users`, not `groups_id`
- write a plain password value if helper signatures differ across versions
- call `env.cr.commit()` before leaving the shell so the browser can see the records

### 2. Restart Odoo after model or view changes

If Python models, XML views, or manifests changed, restart the running service before opening the website.

```bash
docker compose restart odoo
```

Without a restart, the browser may hit stale-runtime errors even when tests passed. During verification of the tournament registration page, a stale process raised an `AttributeError` for a newly added tournament field until the container was restarted.

### 3. Verify the website flow in a browser

Open the registration page directly:

```text
http://localhost:10019/tournament/<tournament_id>/register
```

Then confirm all of the following:
- anonymous access redirects to login because the route uses `auth="user"`
- after login, the page renders without server errors
- the Team dropdown only shows selectable teams
- the page shows an "Unavailable Teams" section with explicit reasons for exclusions
- tournament category and gender badges match the seeded data

### 4. Check live logs when the browser does not match expectations

Use the running container logs immediately after reproducing the issue:

```bash
docker compose logs --tail=200 odoo
```

This is the fastest way to distinguish between:
- routing issues
- stale runtime state
- missing upgraded fields
- template rendering errors

## Required Changes in Existing Modules

**None.** The module is designed to work purely as an extension. It:
- Inherits `federation.season.registration` to add states and fields (no breaking changes).
- Inherits `federation.club` to add `representative_ids` One2many (additive only).
- Uses existing `federation.tournament` and `federation.tournament.participant` models as-is.

## Dependencies

- `website` - For public pages and website layout.
- `portal` - For portal layout, pager, and `CustomerPortal` base class.
- `sports_federation_base` - For clubs, teams, seasons, season registrations.
- `sports_federation_tournament` - For tournaments and participants.