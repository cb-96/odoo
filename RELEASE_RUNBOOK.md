# Release Runbook

Last updated: 2026-04-17
Owner: Federation Platform Team
Last reviewed: 2026-04-17
Review cadence: Every release
Release train: 2026.04

This runbook is the canonical operator checklist for promoting the federation
stack with repeatable verification, upgrade, and rollback steps.

## Preconditions

1. Confirm the target branch is merged and the working tree is clean enough to
   identify the intended release diff.
2. Confirm Docker services are healthy with the production compose file.
3. Confirm enough disk space exists for both a PostgreSQL dump and a filestore
   archive under `./backups/`.

## Documentation Freshness

Before cutting a release, verify that the freshness-tracked docs still match the
change set whenever route ownership, architecture, CI policy, or operational
guidance changed:

```bash
python3 addons/ci/check_doc_freshness.py
python3 addons/ci/check_markdown_links.py
python3 addons/ci/check_module_owners.py
python3 addons/ci/check_openapi_contracts.py
```

If the release changed any tracked surface, update the affected document or
archive it in the same release branch before proceeding.

If the release changed portal privilege boundaries, reporting SQL view policy,
or canonical public route ownership, review the affected record under `adr/`
and update it in the same release branch when the decision changed.

If the release includes model, view, or controller ownership changes, confirm
the migration-review gate passes and that every affected module has either
release-note coverage or an explicit migration script:

```bash
python3 addons/ci/check_migration_review.py --base-ref origin/main
```

If the release changes addon responsibility boundaries or adds a new
`sports_federation_*` module, update `MODULE_OWNERS.yaml` in the same release
branch and rerun the registry check before cutting the release.

## Pre-Release Verification

Run the focused suites that cover the highest-risk federation workflows:

```bash
bash addons/ci/run_tests.sh --suite portal_public_ops
bash addons/ci/run_tests.sh --suite finance_reporting
bash addons/ci/run_tests.sh --suite release_surfaces
```

These suites now include query-budget regression checks for the public-site,
portal, and reporting hotspots documented in `PERFORMANCE_BASELINES.md`.

If the release changes only one module, also run that module directly before the
broader suites:

```bash
bash addons/ci/run_tests.sh --module sports_federation_reporting
```

## Upgrade Dry Run

Print the resolved module list and backup target before touching the database:

```bash
./scripts/upgrade_sports_federation.sh --db odoo --dry-run
```

If you need to restrict the release to a subset of installed modules:

```bash
./scripts/upgrade_sports_federation.sh --db odoo --modules sports_federation_reporting,sports_federation_portal --dry-run
```

## Backups

The upgrade script performs backups by default. It stores:

- `modules.txt` with the exact upgraded module list
- `<db>_<timestamp>.dump` as a PostgreSQL custom-format dump
- `filestore_<db>_<timestamp>.tar.gz` when a filestore exists under
  `./odoo-data/filestore/<db>`

Do not use `--skip-backup` for production releases.

Run the periodic restore drill against one of these backup directories before
or during each release train using `RESTORE_VERIFICATION_CHECKLIST.md` as the
operator checklist:

```bash
bash addons/ci/restore_backup_drill.sh --backup-dir 2026-04-15_191410 --target-db odoo_restore_drill --dry-run
```

## Production Upgrade

Run the upgrade and let the script restart the live Odoo service afterward so
Python changes are loaded by the running web container:

```bash
./scripts/upgrade_sports_federation.sh --db odoo --yes
```

The script runs:

- `odoo -c /etc/odoo/odoo.conf -d <db> -u <module_csv> --stop-after-init`
- `docker compose restart odoo`

## Post-Upgrade Verification

Verify these operator checkpoints immediately after the upgrade:

1. Open Federation > Reporting > Operator Checklist and confirm there are no
   unexpected blocked queues.
2. Open Federation > Reporting > Report Schedules and confirm there are no new
   `Last Run Failed` schedules.
3. Open Federation > Import Tools > Inbound Deliveries and confirm there are no
   unexpected `failed` or `processed_with_errors` deliveries.
4. Validate the public and portal release surfaces manually if the release
   touched them:
   - `/web/login`
   - `/tournaments`
   - `/tournaments/<slug>/register`
   - `/my/teams/new`
   - `/my/season-registration/new`
   - `/my/compliance`
5. Trigger one scheduled report manually from Federation > Reporting > Report
   Schedules if the release touched reporting code.

## Rollback

If the upgrade must be rolled back:

1. Stop or scale down the Odoo service to prevent new writes.
2. Restore the PostgreSQL dump from the relevant backup directory.
3. Restore the matching filestore archive.
4. Restart the Odoo service.
5. Re-run the post-upgrade verification checklist against the restored system.

Example restore outline:

```bash
docker compose stop odoo
dropdb -U odoo odoo
createdb -U odoo odoo
pg_restore -U odoo -d odoo backups/<timestamp>/odoo_<timestamp>.dump
tar -xzf backups/<timestamp>/filestore_odoo_<timestamp>.tar.gz -C odoo-data/filestore
docker compose up -d odoo
```

Adjust database names and paths to match the selected backup directory.