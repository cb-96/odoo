# Compatibility Inventory

Last updated: 2026-04-13

This inventory tracks every intentional compatibility surface that remains in the
current release window. Nothing in this list is accidental: each alias or
legacy input has an owner, a review date, and a target exit date.

| Surface | Canonical Replacement | Why It Still Exists | Owner | Review By | Target Exit |
|---|---|---|---|---|---|
| `/competitions`, `/competitions/archive`, `/competitions/api/json` | `/tournaments`, `/tournaments/api/json` | Existing bookmarks, embeds, and portal links still resolve through the older competition vocabulary. | `sports_federation_public_site` maintainers | 2026-06-30 | 2026-10-01 |
| Numeric public tournament and season routes: `/tournament/<id>`, `/tournament/<id>/register`, `/tournament/<id>/schedule.ics`, `/season/<id>` | Slug-first routes under `/tournaments/<slug>` and `/seasons/<slug>` | Older emails, PDFs, QR codes, and exported references still point at numeric identifiers. | `sports_federation_public_site` maintainers | 2026-06-30 | 2026-10-01 |
| `/api/v1/tournaments/<id>/feed`, `/api/v1/competitions/<id>/feed` | `/api/v1/tournaments/<slug>/feed` | One release-cycle grace period for external consumers still using numeric or competition-named feed URLs. | `sports_federation_public_site` and integration maintainers | 2026-06-30 | 2026-10-01 |
| Player import `name` column fallback | Explicit `first_name`, `last_name` columns | Historical rollover spreadsheets still deliver single-column player names. | `sports_federation_import_tools` maintainers | 2026-07-15 | 2026-10-15 |
| Team import `club_name` fallback and `team_name` / `name` aliasing | `club_code` and explicit team naming columns | Club onboarding files are still mixed between name-based and code-based references. | `sports_federation_import_tools` maintainers | 2026-07-15 | 2026-10-15 |
| Tournament participant import `tournament_name` and `team_name` fallbacks | `tournament_code` and `team_code` | Federation operators still receive legacy participant sheets without stable codes. | `sports_federation_import_tools` maintainers | 2026-07-15 | 2026-10-15 |

Removal policy:

- Remove a compatibility surface only after its replacement is documented,
  covered by tests, and announced in the module README plus
  `INTEGRATION_CONTRACTS.md` when the surface is partner-facing.
- If a review date passes without a removal decision, extend both the review and
  target exit dates in this file within the same change set that justifies the
  delay.