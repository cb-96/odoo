---
name: ci-scope-selector
description: 'Chooses the smallest safe CI scope for this repo from changed files or module names. Use when deciding which module CI, named suite, or full CI to run after a change.'
argument-hint: 'Changed files, modules, or ask it to inspect the current worktree'
user-invocable: true
---

# CI Scope Selector

## What This Skill Produces

This skill chooses the smallest safe CI scope for the current change: per-module runs, named suite runs, and whether a final full CI run is recommended.

Use it when:
- you are not sure which module tests to run
- changed files span multiple addons
- you want to avoid jumping straight to full CI
- you need a repeatable argument for why broader validation is required

## Repo Facts

- CI entrypoint: `bash ./ci/run_tests.sh`
- Named suites:
  - `competition_core`
  - `portal_public_ops`
  - `finance_reporting`

## Fast Path

Use the helper script:

- [select_ci_scope.sh](./scripts/select_ci_scope.sh)

Examples:

```bash
bash .github/skills/ci-scope-selector/scripts/select_ci_scope.sh
bash .github/skills/ci-scope-selector/scripts/select_ci_scope.sh sports_federation_portal/models/federation_team_roster.py
git diff --name-only HEAD | bash .github/skills/ci-scope-selector/scripts/select_ci_scope.sh
```

When no file paths are passed, the script inspects the current git worktree.

## Procedure

1. Gather changed files.
   - Use explicit file paths from the user, or the current worktree when nothing is provided.

2. Map files to owning addons.
   - If a path sits under `sports_federation_*`, that addon is the first module to test.
   - Treat `ci/`, `.github/workflows/`, and top-level repo docs as cross-cutting signals.

3. Start with per-module CI.
   - Each changed addon should normally get its own `--module` run first.

4. Check for suite coverage.
   - If all changed addons fit inside one named suite, run that suite next instead of full CI.
   - If changes span unrelated families or CI wiring, prepare for a final full run.

5. Escalate only when justified.
   - Shared services, multiple addon families, CI scripts, or top-level architecture docs are reasons to broaden.

## Decision Rules

### Prefer module CI first when

- one addon owns the change
- the change is local to views, models, tests, or README in that addon

### Prefer suite CI when

- all changed addons fit within one named suite
- portal/public changes are confined to `portal_public_ops`
- competition, standings, and result flow changes fit inside `competition_core`
- finance bridge and reporting changes fit inside `finance_reporting`

### Prefer final full CI when

- `ci/` or `.github/workflows/` changed
- multiple addon families are involved
- shared core seams changed and no single suite covers them safely
- top-level docs such as `CONTEXT.md`, `TECHNICAL_NOTE.md`, or ownership matrices changed alongside code

## Quality Bar

The output should always include:
- changed addons
- suggested per-module commands
- suggested suite commands when applicable
- whether final full CI is recommended and why

## Example Invocations

- `/ci-scope-selector inspect the current worktree and tell me the smallest safe CI scope`
- `/ci-scope-selector these files changed: sports_federation_portal/controllers/rosters.py and sports_federation_portal/tests/test_roster_portal_access.py`
- `/ci-scope-selector decide whether this needs module CI, portal_public_ops, or full CI`