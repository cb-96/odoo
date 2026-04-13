---
name: portal-access-fixtures
description: 'Builds repeatable portal ownership and access fixtures for this repo. Use when changing sports_federation_portal flows, club-representative ownership, roster management, portal registration, or portal record-rule behavior.'
argument-hint: 'Describe the portal flow or ownership rule you are changing'
user-invocable: true
---

# Portal Access Fixtures

## What This Skill Produces

This skill builds the smallest realistic fixture set for portal and ownership behavior in this repository and turns it into repeatable tests.

Use it when:
- adding or changing `sports_federation_portal` controllers
- adding portal helper methods on models
- changing club representative ownership rules
- adding roster, season registration, or tournament registration portal flows
- testing positive and negative access paths for portal users

## Repo Pattern To Follow

The strongest current example is:
- `sports_federation_portal/tests/test_roster_portal_access.py`

That pattern uses `TransactionCase` and validates model/helper behavior with `with_user(...)` instead of only relying on controller rendering.

## Core Fixture Recipe

1. Create the portal group.
   - `sports_federation_portal.group_federation_portal_club`

2. Create the representative role type.
   - `sports_federation_portal.role_type_competition_contact`

3. Create shared domain fixtures.
   - season
   - two clubs
   - one or more teams per club

4. Create portal users.
   - use `.with_context(no_reset_password=True).create(...)`
   - assign groups with `group_ids`, not `groups_id`

5. Link each user to their club through `federation.club.representative`.

6. Create the workflow records the portal flow depends on.
   - season registrations
   - tournament registrations
   - rosters and roster lines
   - matches and match sheets
   - players and licenses when roster eligibility matters

7. Move prerequisites to the required state.
   - confirm registrations when the portal flow requires confirmed registrations
   - activate rosters when visibility or downstream operations rely on active state

8. Assert both positive and negative paths.
   - own-club records are visible
   - foreign-club records are hidden or forbidden
   - forbidden writes raise `AccessError`
   - invalid business prerequisites raise `ValidationError`

## Testing Strategy

Prefer `TransactionCase` first when the behavior is owned by model helpers or record rules.

Use `with_user(user)` for access assertions.

Use `sudo()` only where the code under test explicitly intends elevated behavior. If a portal helper uses `sudo()`, the test should still prove the helper rejects foreign-club access before relying on elevated writes.

## Decision Points

### If you are testing a portal helper method

Test the helper directly in `TransactionCase` before adding route-level tests.

### If you are testing a record rule or search visibility issue

Use `.with_user(user).search([])` and assert inclusion/exclusion explicitly.

### If you are testing a create flow that depends on prior confirmation

Create the registration in draft first, assert `ValidationError`, then confirm it and assert the happy path.

### If the picker should be filtered

Add at least one same-club allowed record and one disallowed record by gender, club, team, or season.

## Quality Bar

Finish only when tests prove:
- own-club access works
- foreign-club access is denied
- write paths are intentionally allowed or intentionally blocked
- prerequisite-state validation is explicit
- the fixture is compact and reusable

## Example Invocations

- `/portal-access-fixtures add tests for a new roster portal helper with own-club and foreign-club coverage`
- `/portal-access-fixtures build the fixture set for a tournament registration portal flow`
- `/portal-access-fixtures verify portal record rules for match sheets and roster audit records`