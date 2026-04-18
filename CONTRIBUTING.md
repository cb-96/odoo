# Contributing

This repository expects small, test-backed changes with matching documentation updates.

## Prerequisites

- Python 3.10 or newer for local linting
- Docker with Compose v2 for the containerized Odoo test runner
- Git Bash, WSL, or another POSIX shell for the `ci/*.sh` scripts on Windows

## Local setup

```bash
cp ci/.env.example ci/.env
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Keep `ci/.env` local-only. Integration keys can be copied from `ci/integrations.env.example` or provided by your shell environment.

## Focused test commands

Run targeted suites for the main maintained flows:

```bash
bash ./ci/run_tests.sh --suite competition_core
bash ./ci/run_tests.sh --suite portal_public_ops
bash ./ci/run_tests.sh --suite finance_reporting
```

Run an individual module when you only need a narrow slice:

```bash
bash ./ci/run_tests.sh --module sports_federation_result_control
```

List the named suites from the runner itself:

```bash
bash ./ci/run_tests.sh --list-suites
```

## Pre-push checks

```bash
black --check sports_federation_base sports_federation_tournament sports_federation_standings sports_federation_venues sports_federation_portal sports_federation_public_site ci
flake8 sports_federation_base sports_federation_tournament sports_federation_standings sports_federation_venues sports_federation_portal sports_federation_public_site ci
bash -n ci/run_tests.sh
bash -n ci/apply_env_to_ir_config.sh
bash -n ci/restore_backup_drill.sh
python3 ci/check_doc_freshness.py
python3 ci/check_markdown_links.py
python3 ci/check_module_owners.py
python3 ci/check_openapi_contracts.py
python3 ci/check_release_train.py
```

## Documentation expectations

- Update the relevant module README for behavior or schema changes.
- Update the matching workflow under `_workflows/` when business behavior changes.
- Keep `TECHNICAL_NOTE.md`, `CONTEXT.md`, `INTEGRATIONS.md`, and `STATE_AND_OWNERSHIP_MATRIX.md` aligned when the change affects their scope.
- Update `MODULE_OWNERS.yaml` whenever a new addon is introduced or primary module ownership changes.
- Update `RELEASE_TRAIN.md` when a change starts a new release window or needs train-level migration coordination.
- Update the relevant record under `adr/` when a change revises portal trust boundaries, reporting SQL-view policy, or public route ownership.
