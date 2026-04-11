---
name: install-failure-triage
description: 'Triages Odoo module install and upgrade failures in this sports federation repo. Use when CI fails during module install, registry build, XML loading, ACL setup, manifest loading, or view validation, then fix the root cause and rerun focused CI.'
argument-hint: 'Failing module or suite, plus whether to stop at diagnosis or keep fixing until green'
user-invocable: true
---

# Install Failure Triage

## What This Skill Produces

This skill investigates module install or upgrade failures in this repository, classifies the failure into the right bucket, fixes the smallest root cause, and reruns focused CI until the failing install path is green.

Use it when:
- a module fails before tests even begin
- Odoo crashes while loading manifests, views, ACLs, or registry models
- CI reports `ParseError`, `KeyError`, missing external IDs, or invalid field/view errors
- a change in one addon breaks module-scoped installs in another addon

This is repository-specific. It assumes the CI entrypoint is `bash ./ci/run_tests.sh` from the repo root.

## Primary Checks

Check these files first:
- `__manifest__.py`
- `models/__init__.py`, `wizards/__init__.py`, `controllers/__init__.py`
- `security/ir.model.access.csv`
- XML files under `views/`, `security/`, and `data/`
- `ci/run_tests.sh` and the newest `ci/logs/<timestamp>/` directory

## Procedure

1. Narrow the failing scope.
   - Start with `bash ./ci/run_tests.sh --module <module>` for the failing addon.
   - If the user only gave a traceback, infer the module from the changed files or the failing external IDs.

2. Read the newest CI logs in this order.
   - `summary.log`
   - `errors.log`
   - the relevant traceback region in `raw.log`

3. Classify the install failure before editing.
   - **Manifest / dependency**: missing `depends`, missing `data` registration, wrong load order.
   - **Python import / export**: file created but not exported in `__init__.py`.
   - **Security / external ID**: broken ACL model reference, wrong owner module in XML IDs, missing groups.
   - **XML / view**: invalid xpath, missing field, invalid `view_mode`, malformed domain/context, bad attributes.
   - **Registry / model availability**: code accesses a model that is not installed in module-scoped CI.
   - **Schema / field**: stored field definition drift, missing field name, invalid comodel.

4. Fix the smallest real cause.
   - Do not patch around symptoms in tests when the install graph is wrong.
   - Keep the fix in the owning module whenever possible.

5. Re-run focused module CI.
   - If the failure came from a shared seam, rerun each directly affected module.
   - Broaden to a suite or full CI only after the install path is green.

## Repo-Specific Failure Patterns

Watch for these repeatedly in this repo:
- Odoo 19 view updates often require `list,form` instead of `tree,form` in action `view_mode`.
- New models usually need ACL rows in `security/ir.model.access.csv` and registration in `__manifest__.py`.
- Portal and cross-module ACL references must use the model XML ID owned by the correct addon.
- Optional addon seams should use safe lookup such as `env.get("model.name")` instead of direct registry access.
- Workflow or user-facing behavior changes usually require doc updates in module `README.md` and `_workflows/*.md`.

## Decision Points

### If the traceback mentions `External ID not found`

Check:
- `__manifest__.py` load order
- typo in XML ID
- wrong module prefix for model or group reference

### If the traceback mentions a missing field in a view

Check:
- field exported from the right Python file
- inherited addon listed in `depends`
- xpath targets still valid in the parent view

### If the traceback is a registry `KeyError`

Check:
- direct registry access to optional models
- module-scoped CI running without the provider addon installed
- safe guards around optional behaviors

### If the failure appears before tests but after some modules load

Assume install wiring first, not business logic.

## Quality Bar

Do not stop at “the traceback changed.” Finish only when:
- focused CI for the failing module exits cleanly
- the install path succeeds without masking the root cause
- a regression test is added if the failure came from business behavior or an optional seam
- relevant docs are updated if the install failure came from a workflow or user-facing change

## Useful Repo Anchors

- `CONTRIBUTING.md`
- `.github/copilot-instructions.md`
- `_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md`

## Example Invocations

- `/install-failure-triage sports_federation_portal fails to install in CI; fix it until green`
- `/install-failure-triage investigate this ParseError during module load and patch the owning module`
- `/install-failure-triage find the first real install failure in CI logs and rerun focused module CI`