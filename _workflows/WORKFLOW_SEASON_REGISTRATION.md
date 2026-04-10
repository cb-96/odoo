# Workflow: Season Registration

End-to-end process for setting up a new season and registering clubs, teams, and
players — from season creation through club enrolment to individual licensing.

## Overview

Every competitive year begins with a **season** that scopes all competitions,
registrations, rosters, and licenses. Clubs register for the season, enrol their
teams, and players receive licenses that certify their eligibility to compete.

## Modules Involved

| Module | Role |
|--------|------|
| `sports_federation_base` | Season, club, team, and season-registration models |
| `sports_federation_people` | Player records and license creation |
| `sports_federation_portal` | Club representative self-service registration |
| `sports_federation_compliance` | Document requirements linked to registration |
| `sports_federation_finance_bridge` | Registration fee events |
| `sports_federation_notifications` | Registration reminders and confirmations |

## Step-by-Step Flow

### 1. Season Creation

**Actor**: Federation administrator
**Module**: `sports_federation_base`

1. Navigate to **Federation → Configuration → Seasons**.
2. Create a new season with name, code, and date range (e.g. "2025-2026").
3. Set the season state to **open**.

The season record becomes the scoping key for all registrations, tournaments,
rosters, and licenses throughout the year.

### 2. Club Registration Opening

**Actor**: Federation administrator
**Module**: `sports_federation_base`

1. Navigate to **Federation → Registrations → Season Registrations**.
2. Create registration records (one per team) or let clubs self-register via the portal.
3. Each registration links a team and its club to an open season.

Registration states: `draft` → `submitted` → `confirmed` / `cancelled`.

### 3. Portal Self-Service (Optional)

**Actor**: Club representative (portal user)
**Module**: `sports_federation_portal`

1. Club representative logs into the portal.
2. Navigates to the federation registration section.
3. Submits their club's season registration request.
4. Adds supporting notes when needed.
5. Registration is created in `submitted` state for federation review.

### 4. Registration Review & Approval

**Actor**: Federation administrator
**Module**: `sports_federation_base`

1. Review submitted registrations from the backend review screen.
2. Verify club ownership, season status, and any federation prerequisites.
3. **Confirm** the registration or **reject** it back to `draft` with a rejection reason.
4. Confirmed teams are eligible to enrol players and proceed into competition operations.

There is no persistent `rejected` season-registration state in the current model. Rejection is represented by the record returning to `draft` while keeping `rejection_reason` for follow-up.

### 5. Team Enrolment

**Actor**: Club administrator or federation staff
**Module**: `sports_federation_base`

1. Under each confirmed club registration, create or confirm teams for the season.
2. Teams inherit the club's season registration scope.
3. Teams become available for tournament participation and roster creation.

### 6. Player Registration & Licensing

**Actor**: Federation administrator
**Module**: `sports_federation_people`

1. Create or update player records with club affiliation.
2. Create a **player license** linked to the active season and club.
3. License receives an auto-generated number via `ir.sequence` (`FED-LIC-XXXXX`).
4. Set license state: `draft` → `active`.

Players must hold an active license for the current season to be eligible for
rosters and match sheets.

### 7. Compliance Document Collection

**Actor**: Club representative or federation staff
**Module**: `sports_federation_compliance`

1. Federation defines document requirements per entity type (club, player, etc.).
2. Clubs upload required documents (insurance, safety certificates, etc.).
3. Federation staff reviews submissions: `submitted` → `approved` / `rejected`.
4. Compliance checks are run to flag missing or expired documents.

### 8. Fee Recording

**Actor**: Federation administrator
**Module**: `sports_federation_finance_bridge`

1. Upon registration confirmation, a finance event is created for the registration fee.
2. The default catalogue fee type code is `season_registration` (created on demand
    as "Season Registration Fee" if it does not exist yet).
3. Finance event follows: `draft` → `confirmed` → `settled` / `cancelled`.

### 9. Notifications

**Actor**: System (automated)
**Module**: `sports_federation_notifications`

- Registration confirmation and rejection emails are logged and sent to the submitting club representative.
- Reminders for incomplete or stale draft registrations (cron job).
- Missing-document notices triggered by compliance checks.

## State Diagram

```
Season: draft → open → closed

Registration: draft → submitted → confirmed
                                 → cancelled
                                 ↘ draft (via rejection)

License: draft → active → expired
                        → revoked
```

## Key Decision Points

| Question | Outcome |
|----------|---------|
| Are all compliance documents submitted? | Block approval until compliant |
| Is the registration fee paid? | Registration can proceed but fee remains tracked |
| Has the club been sanctioned? | Governance override may be needed |

## Related Workflows

- [Tournament Lifecycle](WORKFLOW_TOURNAMENT_LIFECYCLE.md) — tournaments open to registered clubs
- [Compliance Management](WORKFLOW_COMPLIANCE_MANAGEMENT.md) — document collection detail
- [Financial Tracking](WORKFLOW_FINANCIAL_TRACKING.md) — fee handling detail
