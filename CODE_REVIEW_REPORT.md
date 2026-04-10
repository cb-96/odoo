Progress: Completed a full repo scan (manifests, READMEs, security, controllers, views, workflows, and tests). Below is the structured report.

**Summary**
- **Status**: Well-structured Odoo 19 addon collection with focused modules and good inline documentation.
- **Tests**: Many modules include unit/integration tests, but there is no CI to run them automatically.
- **Overall risk**: **Medium** — code quality and docs are good; primary risks are missing CI/packaging, a few controller/template security patterns (`sudo()` usage, `t-raw`), and a documentation/packaging mismatch (`requirements.txt` referenced but missing).

**Module Inventory**
- **sports_federation_base**: Base models (clubs, teams, seasons). Has: **models**, **views**, **security**, **data**. Tests: **no** tests/ dir. Manifest includes sequences and view files.  
- **sports_federation_competition_engine**: Scheduling wizards & services. Has: **models**, **wizards**, **services**, **views**, **security**, **tests**. Tests: **present**.  
- **sports_federation_compliance**: Document requirements/submissions. Has: **models**, **views**, **security**, **tests**. Tests: **present**.  
- **sports_federation_discipline**: Incidents and sanctions. Has: **models**, **views**, **security**, **data**, **tests**. Tests: **present**.  
- **sports_federation_finance_bridge**: Finance-event bridge. Has: **models**, **views**, **security**, **tests**. Tests: **present**.  
- **sports_federation_governance**: Override requests & audit. Has: **models**, **views**, **security**, **tests**. Tests: **present**.  
- **sports_federation_import_tools**: CSV import wizards. Has: **views**, **security**, **tests**, `wizard/` (singular) folder (note: naming inconsistency vs `wizards/`). Tests: **present**.  
- **sports_federation_notifications**: Notification service, templates, crons. Has: **models**, **views**, **data**, **security**, **tests**. Tests: **present**.  
- **sports_federation_officiating**: Referee registry & assignments. Has: **models**, **views**, **security**. Tests: **absent** (no tests/ dir observed).  
- **sports_federation_people**: Player master & licenses. Has: **models**, **views**, **data**, **security**. Tests: **absent**.  
- **sports_federation_portal**: Portal controllers + portal extensions. Has: **controllers**, **models**, **views**, **data**, **security**, **tests**. Tests: **present**.  
- **sports_federation_public_site**: Public website controllers/templates. Has: **controllers**, **views**, **security**, **tests**. Tests: **present**.  
- **sports_federation_reporting**: SQL-view based reports and CSV exports. Has: **controllers**, **views**, **security**, **tests**. Tests: **present**.  
- **sports_federation_result_control**: Result submit/verify/approve workflow. Has: **controllers**, **models**, **views**, **security**, **tests**. Tests: **present**.  
- **sports_federation_rosters**: Team rosters and match sheets. Has: **models**, **views**, **security**, **tests**. Tests: **present**.  
- **sports_federation_rules**: Rule sets, tie-breaks, eligibility. Has: **models**, **views**, **security**. Tests: **absent** (no tests/ dir observed).  
- **sports_federation_standings**: Standings computation and tie-break notes. Has: **models**, **views**, **security**, **tests**. Tests: **present** (good coverage for tie-break logic).  
- **sports_federation_tournament**: Tournaments, stages, matches (central hub). Has: **models**, **views**, **services**, **security**, **tests**. Tests: **present**.  
- **sports_federation_venues**: Venues and `gameday`. Has: **models**, **views**, **security**, **tests**. Tests: **present**.

(Notes: all modules have a `security/ir.model.access.csv` file present in their `security/` folder.)

**Key top-level files**
- **CONTEXT.md**: [CONTEXT.md](CONTEXT.md#L1-L20) — concise overview; references workflows and modules; updated with 2026-04-07 additions.
- **TECHNICAL_NOTE.md**: [TECHNICAL_NOTE.md](TECHNICAL_NOTE.md#L1-L20) — detailed architecture + explicit “Last updated: 2026-04-07”; contains migration & testing guidance.
- **_workflows/**: [odoo/_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md#L1-L10) and related workflow files — authoritative behaviour specs.
- **ROADMAP.md**: [ROADMAP.md](ROADMAP.md#L1-L20) — project roadmap linked to modules and test tasks.
- **README.md**: [README.md](README.md#L1-L40) — local quickstart references `requirements.txt` (this file is missing; see Issues).

All top-level docs appear up-to-date (edits dated 2026-04-07). The workflow docs are the canonical behavioural spec.

**Issues & Risks**
- **Missing pinned dependencies**: README references `requirements.txt` but that file is not present (no `requirements.txt` in repo). This blocks reproducible dev/test environments and CI.  
- **No CI / automation**: No `.github/workflows` detected (no automatic test/lint runs). Tests exist but are not executed by CI; risk of regressions.  
- **Controller `sudo()` usage**: Public/portal controllers use `sudo()` repeatedly (reads and also writes via `sudo().create()` and `sudo().action_submit()`) — see [sports_federation_portal/controllers/main.py](sports_federation_portal/controllers/main.py#L1-L200) and [sports_federation_public_site/controllers/public_competitions.py](sports_federation_public_site/controllers/public_competitions.py#L1-L120). Writes executed under `sudo()` bypass ACLs; audit is required to ensure thorough server-side validation and to limit fields created/returned.  
- **Template XSS surface**: templates render `public_description` with `t-raw` in [sports_federation_public_site/views/website_templates.xml](sports_federation_public_site/views/website_templates.xml#L31) and (#L90) — if `public_description` can be populated by non-admins this is an XSS risk.  
- **Inconsistent folder naming**: `sports_federation_import_tools` uses `wizard/` (singular) while other modules use `wizards/` — a maintenance/inconsistency issue (not functional but confusing). See [sports_federation_import_tools/README.md](sports_federation_import_tools/README.md#L1-L20).  
- **Upgrade/migration risk**: New models/fields (gameday, bracket fields, stage.progression, tournament.round) were added recently (see `TECHNICAL_NOTE.md`); these changes may require DB migration scripts for production upgrades.  
- **Packaging / release gaps**: No `pyproject.toml` / `setup.cfg` / `requirements.txt` / pre-commit config found; recommend adding packaging + lint config.  
- **Tests not run in CI**: Many modules include tests (good), but without CI they are not regularly validated.

**CI / DevOps**
- **CI presence**: None detected (no `.github/workflows/` or other CI config).
- **Lint / format**: No `.flake8`, `.pylintrc`, `pyproject.toml`, or `pre-commit` config found.
- **Requirements**: No `requirements.txt` or `pyproject.toml` — README refers to `pip install -r requirements.txt`, but file is missing.
- **Test runner**: Tests are written as Odoo module tests. To run locally (example):
```bash
python odoo-bin -d test_db -i sports_federation_competition_engine --test-enable --stop-after-init
```
(Replace `sports_federation_competition_engine` with any module name.)

**Prioritized recommendations (top 5)**
- **CI + Test Automation**: Add GitHub Actions pipeline that installs dependencies, runs `odoo` module tests, and runs linters (urgent — reduces regression risk). Rationale: tests exist but not executed automatically.
- **Add pinned dependencies**: Add a `requirements.txt` or `pyproject.toml` (with pinned versions) referenced by README and CI. Rationale: reproducible dev/test builds and deterministic CI runs.
- **Security audit of controllers & templates**: Review all `auth="public"` and `auth="user"` controllers for `sudo()` usage and replace unsafe write patterns; sanitize `t-raw` usage or restrict who can edit HTML fields. Rationale: prevents ACL bypass and XSS.
- **State/ownership matrix + tests**: Create `STATE_AND_OWNERSHIP_MATRIX.md` and add tests that assert standings exclude contested/unapproved results (as recommended in roadmap). Rationale: reduces logical regressions in progression/standing computations.
- **Add CI lint + pre-commit**: Add `pre-commit` and basic `flake8/black` config; run these in CI. Rationale: enforces consistent style and catches obvious issues early.

**Candidate roadmap items (6–10)**
- Add GitHub Actions for test/lint/manifest validation.
- Add pinned dependencies and reproducible dev environment (`requirements.txt`/`pyproject.toml`).
- Audit & harden public/portal controllers (security sprint).
- Add migration/upgrade scripts and release notes for recent model changes (gameday, bracket fields).
- Expand test coverage for scheduling (round-robin/knockout), progression, and gameday constraints.
- Implement eligibility service (centralized eligibility checks) per roadmap.
- Add public API rate limits and monitoring for `public_site` endpoints.
- Add KPI dashboards & CSV endpoints in `reporting` and wire export tests.
- Add pre-commit and CI gate for manifest/data consistency.

**Files needing immediate attention**
- **README / missing deps**: README.md references `requirements.txt` but the file is missing — [README.md](README.md#L60-L80). Action: add pinned `requirements.txt` or update docs.
- **Portal controller writes via sudo**: [sports_federation_portal/controllers/main.py](sports_federation_portal/controllers/main.py#L120-L160) — creates registrations with `sudo().create()` and immediately calls `sudo().action_submit()`; audit validation and avoid ACL bypass on writes.
- **Public template raw HTML**: [sports_federation_public_site/views/website_templates.xml](sports_federation_public_site/views/website_templates.xml#L31) — `t-raw="tournament.public_description[:150]"`, and [sports_federation_public_site/views/website_templates.xml](sports_federation_public_site/views/website_templates.xml#L90) — full description rendered raw; ensure HTML originates from trusted users or sanitize.
- **Import tools folder naming**: `sports_federation_import_tools` uses `wizard/` (singular) (see [sports_federation_import_tools/README.md](sports_federation_import_tools/README.md#L1-L20)); consider standardizing to `wizards/`.
- **No CI manifests**: Add a `.github/workflows` CI pipeline (no link — folder missing). Action: create CI workflow to run tests + lint.
- **Migration/upgrade notes**: `TECHNICAL_NOTE.md` documents new models (2026-04-07); ensure DB migration scripts exist (see [TECHNICAL_NOTE.md](TECHNICAL_NOTE.md#L1-L10)).

**TODO / FIXME occurrences (found)**
- [README.md](README.md#L112): context mentions adding TODO in PR process ("TODO in the change and notify maintainers."). (Doc-level.)
- [.github/copilot-instructions.md](.github/copilot-instructions.md#L57): guidance references leaving a TODO if docs cannot be updated. (Doc-level.)
- [sports_federation_notifications/models/notification_service.py](sports_federation_notifications/models/notification_service.py#L73-L81): string usage includes `mail.mail_activity_data_todo` / "todo" (not a code TODO but a default activity type). (Not action-critical.)

(Overall: no large number of inline TODO/FIXME markers in code — mostly documentation notes.)

How to verify things I couldn’t (tests/CI)
- To run module tests locally (replace module name as needed):
```bash
python odoo-bin -d test_db -i <module_name> --test-enable --stop-after-init
```
- To validate CI: add a minimal GitHub Actions workflow that sets up Python/postgres, installs pinned deps, and runs the above test command for each module. I can scaffold this for you.

Next steps I can take (pick one)
- Scaffold a GitHub Actions CI workflow that runs tests + flake8 and push as a draft PR.
- Create a `requirements.txt` / `pyproject.toml` (I can propose pinned versions) and update README.
- Run a focused code audit patch that replaces unsafe `sudo()` writes in portal controllers with safe ORM operations and tighter validation (I can prepare a patch and tests).

Which of the next steps would you like me to do first?
