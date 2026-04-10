<!-- ROADMAP updated 2026-04-10: archived previous version to ROADMAP_archive_2026-04-07.md -->

# ROADMAP — Engineering Plan (2026-04-10)

This roadmap focuses engineering work into short, verifiable deliverables mapped
to modules. It prioritizes stability (tests & security), CI and reproducible
builds, and the high-value product flows (scheduling, standings, finance
automation, and public/portal UX).

## Vision

Deliver a maintainable, well-tested Odoo addon suite that supports the full
sports federation lifecycle: registration → scheduling → results → standings →
reporting and finance.

## Current snapshot

- Repository contains a well-structured set of `sports_federation_*` modules.
- GitHub Actions CI is defined in `.github/workflows/ci.yml` for targeted lint and module tests.
- Pinned tooling dependencies are defined in `requirements.txt` and lint config in `.flake8`.
- `STATE_AND_OWNERSHIP_MATRIX.md` now documents canonical states and ownership boundaries.
- Public/portal security hardening is in place for visibility gating, portal season-registration ownership, and raw HTML rendering.

## Top priorities (next 30 days)

1. Implemented: add GitHub Actions CI to run targeted module tests and linters.
2. Implemented: add pinned dependencies and document the containerized/local dev setup.
3. Implemented: add `STATE_AND_OWNERSHIP_MATRIX.md` and reconcile lifecycle enums in docs.
4. Implemented: audit public/portal controllers and templates; enforce visibility flags and remove raw `t-raw` rendering.
5. Implemented: keep standings result-filter coverage in place and expand gameday constraint coverage.

## 90-day plan

- Harden progression & eligibility logic: implement a central eligibility service and explainable standings.
- Automate finance events in `sports_federation_finance_bridge` for key triggers.
- Improve public/portal UX and add exportable KPI reports under `sports_federation_reporting`.

## 6-month plan

- Release a v1.0 candidate: stable migrations, packaging, and release notes.
- Add monitoring for public endpoints and basic observability for scheduled jobs.

## Module-targeted deliverables (examples)

- `sports_federation_competition_engine`: add/expand tests for round-robin and knockout, and ensure deterministic scheduling.
- `sports_federation_standings`: tie-break explanation chain and contested/unapproved result filtering tests are in place.
- `sports_federation_finance_bridge`: implement and test auto finance events for registrations and venue fees.
- `sports_federation_public_site` / `sports_federation_portal`: visibility gating and HTML sanitization are in place; continue broader acceptance coverage as follow-up work.

## Quality & release checklist (for each PR that changes models/fields)

- Add or update `security/ir.model.access.csv`.
- Update `__manifest__.py` `data` list when adding XML/CSV data files.
- Include focused unit tests for new behaviour (module-level tests).
- Update module `README.md` with migration notes and behavioural changes.

## Immediate follow-ups

1. Expand CI lint scope as additional legacy files are brought under Black/Flake8.
2. Run the new GitHub Actions workflow and review the first end-to-end result on GitHub.
3. Continue 90-day plan work on eligibility, finance automation, and reporting.

## How to run tests locally

Example (replace `<module>`):

```bash
bash ./ci/run_tests.sh --module <module>
```

## Docs & references

- Workflow specs: [_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md)
- Architecture notes: [TECHNICAL_NOTE.md](TECHNICAL_NOTE.md)
- Project context: [CONTEXT.md](CONTEXT.md)

---

Archived previous roadmap to `ROADMAP_archive_2026-04-07.md`.

Top-priority roadmap items above were implemented in the repository on 2026-04-10.
