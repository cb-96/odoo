# Odoo 19 — Sports Federation Addons (quick context)

Purpose

This workspace contains a collection of Odoo 19 custom addons that implement a sports federation management system: clubs, teams, seasons, tournaments, rules, refereeing, rosters, results verification, standings, portal and public website integration, and reporting.

Where to find things

- Modules: `odoo/` — each addon is named `sports_federation_<domain>` (e.g. `sports_federation_base`, `sports_federation_tournament`, `sports_federation_competition_engine`).
- Authoritative behaviour: `odoo/_workflows/` (e.g. `WORKFLOW_TOURNAMENT_LIFECYCLE.md`, `WORKFLOW_MATCH_DAY_OPERATIONS.md`, `WORKFLOW_RESULT_PIPELINE.md`).
- Architecture notes and developer guidance: `odoo/TECHNICAL_NOTE.md`.
- Module-level implementation notes: `odoo/<module>/README.md` and `_logs/INSTALL_LOG_*.md`.

Core modules (quick)

- `sports_federation_base`: Master data — clubs, teams, seasons, registrations, base security groups.
- `sports_federation_tournament`: Competitions, tournaments, stages, groups, participants, matches and match lifecycle.
- `sports_federation_competition_engine`: Scheduling algorithms and wizards (round-robin, knockout).
- `sports_federation_people`: Player master data and licensing.
- `sports_federation_rosters`: Season rosters and match-sheet management.
- `sports_federation_officiating`: Referee registry and assignments.
- `sports_federation_result_control`: Result submit/verify/approve pipeline and contest/correction flows.
- `sports_federation_standings`: Standings computation and publishing.
- `sports_federation_public_site` / `sports_federation_portal`: Website and portal controllers/templates.

Key workflows (at-a-glance)

- Tournament lifecycle — competition setup, participant enrolment, stage progression, schedule generation, completion. See `odoo/_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md`.
- Match-day operations — roster checks, referee confirmation, match execution, incident logging. See `odoo/_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md`.
- Result pipeline — submit → verify → approve (with contested/corrected exceptions). See `odoo/_workflows/WORKFLOW_RESULT_PIPELINE.md`.
- Public publication — `website_published` toggles, public slugs, and safe public pages for competitions and standings. See `odoo/_workflows/WORKFLOW_PUBLIC_PUBLICATION.md`.

Developer quick-start (most common tasks)

1. Add models: `odoo/<module>/models/<file>.py` and export in `models/__init__.py`.
2. Security: add `security/ir.model.access.csv` and `security/*.xml` record rules.
3. Views: add `views/*.xml` and register in `__manifest__.py` `data`.
4. Wizards/services: put transient models in `wizards/` and algorithmic code in `services/` (competition engine is the canonical location).
5. Tests: put unit/integration tests under `odoo/<module>/tests/` and include at least one focused test for new business logic.
6. Run module tests: `odoo-bin -d <db> -i <module> --test-enable --stop-after-init`.

PR checklist (quick)

- Tests added or updated for the core business behaviour.
- Security ACLs/record rules added.
- `__manifest__.py` updated (depends/data/version) when database changes are introduced.
- Short README or notes added to the module.

Notes for agents/readers

- Prefer the `_workflows` files and `TECHNICAL_NOTE.md` as the source of truth for business behaviour and extension points.
- When proposing code changes, keep modules focused, prefer service classes for algorithms, and add tests demonstrating deterministic behaviour (especially for schedule generation).

If you want, I can expand this summary into a short onboarding checklist, open a PR with the change, or scan `_logs/` and module READMEs to pull in extra context.

