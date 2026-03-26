# Design Note: Sports Federation Club Roles

## Module: `sports_federation_club_roles`

### Overview

This module implements club contacts, club representative roles, and a robust portal ownership model for federation use. It provides a configurable role type system and explicit portal ownership anchoring for club-level access control.

---

## Portal Ownership Strategy

### Core Concept

Portal ownership is anchored through the `federation.club.representative` model, which explicitly maps users to clubs via partner relationships. This provides a clear, auditable ownership chain:

```
res.users (portal user)
    ↓ (user_id)
federation.club.representative
    ↓ (club_id)
federation.club
```

### Key Design Decisions

1. **Explicit User Linking**: Each representative can optionally link to a `res.users` record. This is the primary portal ownership anchor.

2. **Partner-Based Contact**: The `partner_id` field is required, ensuring every representative has a contact record. This supports scenarios where a person represents a club but may not have a portal user yet.

3. **Role-Based Access**: Different role types (competition, finance, safeguarding) can have different portal access needs. The role type flags enable fine-grained access control in portal controllers.

4. **Primary Contact Flags**: The `is_primary` field allows marking one representative per role type per club as the primary contact. This is useful for notifications and default contact resolution.

5. **Temporal Validity**: The `date_start` and `date_end` fields enable tracking representative tenure. The `is_current` computed field provides a convenient filter for active representatives.

### Portal Access Flow

1. **User Authentication**: Portal user logs in with their `res.users` account.

2. **Club Resolution**: The `_get_club_for_user()` or `_get_clubs_for_user()` helper methods resolve which clubs the user represents.

3. **Record Filtering**: Record rules filter records based on the user's representative club IDs.

4. **Access Control**: The `sports_federation_portal.group_federation_portal_club` group controls portal-level access.

### Record Rules

The module includes minimal, readable record rules for portal users:

- **Own Representatives**: Portal users can see their own representative records.
- **Club Representatives**: Portal users can see representatives for clubs they represent.

These rules integrate with the existing `sports_federation_portal` module's record rules for clubs, teams, registrations, etc.

### Why Not Email-Only Matching?

The task specification explicitly warns against relying on shared email only. This design avoids that by:

1. **Explicit User ID Link**: The `user_id` field on `federation.club.representative` provides a direct, unambiguous link.

2. **Partner ID Required**: Even without a portal user, the `partner_id` provides a stable contact reference.

3. **No Email Matching**: Email addresses are not used for ownership resolution. The user-partner-representative chain is the sole ownership path.

---

## Known Limitations

1. **Portal Module Dependency**: The `sports_federation_portal` module already contains a `federation.club.representative` model. This module defines its own version with additional fields. When both modules are installed, the module with higher sequence (or later load order) will take precedence. Consider migrating the portal module to depend on this module instead.

2. **No Notification Workflows**: This module does not build notification workflows. It provides the data structure but does not send emails or notifications when representatives change.

3. **No Organization Chart**: This module does not build a generic organization chart. It focuses on functional roles for club-federation interaction.

4. **Single Club per Representative**: Each representative record links to exactly one club. A person representing multiple clubs needs multiple representative records.

5. **No Portal Views**: This module does not add portal-specific views. Portal views should be added in the `sports_federation_portal` module or a dedicated portal customization module.

---

## Future Extension Points

1. **Portal Controller Integration**: The `_get_portal_ownership_domain()` helper method provides a reusable pattern for building portal record rules. Extend this pattern for new models.

2. **Role-Based Portal Features**: Use the `is_competition_contact`, `is_finance_contact`, and `is_safeguarding_contact` flags to enable role-specific portal features (e.g., only finance contacts can submit invoices).

3. **Notification Workflows**: Add automated notifications when representatives change (e.g., email to federation admin when a new president is appointed).

4. **Representative Approval Workflow**: Add a workflow for approving new representatives (e.g., federation admin must approve before the representative can access the portal).

5. **Representative History**: Extend the model to track historical changes to representative roles and tenure.

6. **Multi-Club Representatives**: Enhance the model to support a single representative record linking to multiple clubs (requires a Many2many relationship).

7. **Delegation**: Add support for delegating representative authority (e.g., a president can delegate to a secretary for specific tasks).

---

## Integration with Existing Modules

### sports_federation_base

- Inherits `federation.club` to add `representative_ids` and smart buttons.
- Reuses existing federation groups (`group_federation_user`, `group_federation_manager`).

### sports_federation_portal

- Defines `federation.club.representative` with additional fields (role types, dates, primary flags).
- Provides helper methods for portal ownership resolution.
- Adds record rules for portal user access.
- Does not modify existing portal controllers or views.

### sports_federation_tournament

- No direct integration. Tournament-related representative roles (e.g., competition contact) can be used by tournament modules.

### sports_federation_people

- No direct integration. People-related data (players, licenses) is separate from club representatives.

---

## Testing

The module includes focused Python tests for:

- Creating multiple representatives for one club
- Role type linkage
- Primary contact behavior
- Date validation
- User/partner ownership mapping logic
- Helper method behavior

Run tests with:

```bash
python -m odoo --test-tags /sports_federation_club_roles
```

---

## Installation

1. Install the module via the Odoo Apps menu.
2. The module automatically creates default role types (competition_contact, finance_contact, safeguarding_contact, president, secretary, admin, other).
3. Add representatives to clubs via the club form or the Club Representatives menu.
4. Link representatives to portal users via the `user_id` field.

---

## Upgrade Notes

- When upgrading from a version without this module, existing `federation.club.representative` records from `sports_federation_portal` will be migrated if the database schema is compatible.
- New fields (`role_type_id`, `is_primary`, `date_start`, `date_end`, `notes`) will be empty for existing records.
- Default role types will be created on first install.