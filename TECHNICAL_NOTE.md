New competition models and behaviours (2026-04-07)

Several new models and scheduling behaviours were added to support more realistic tournaments and automated stage progression:

- `federation.stage.progression` (in `sports_federation_competition_engine`) — a rule model that formalises how teams advance from a source stage/group into a target stage/group. It supports per-group and cross-group selection (`cross_group`), rank windows (`rank_from` / `rank_to`), seeding strategies (`keep_rank`, `reseed`, `random`) and an `auto_advance` flag. Use `action_execute()` to apply a progression and the model is used automatically when standings are frozen and `auto_advance=True`.

- `federation.tournament.round` (in `sports_federation_tournament`) — materialises a logical round inside a stage (useful for per-round scheduling, reporting and tying rounds to `gameday` records). Rounds have a `sequence`, `match_ids` and a simple `state` (draft/scheduled/completed).

- `federation.tournament.template` (in `sports_federation_competition_engine`) — templates to predefine stage/group layouts and progression rules. A template's `action_apply(tournament)` will create stages, groups and progression rules automatically, enabling one-click tournament scaffolding (useful for repeatable event formats).

- `federation.gameday` (in `sports_federation_venues`) — represents a venue/day/time block that bundles multiple matches at the same venue on the same calendar day. When `schedule_by_round` is enabled in the round-robin wizard the scheduler will create or find a `gameday` per round and attach created matches to it.

- Match bracket/linking fields — `federation.match` now includes: `round_id`, `round_number`, `bracket_position`, `bracket_type`, `source_match_1_id`, `source_match_2_id`, `source_type_1/2` and helper `next_match_ids`. These turn matches into first-class bracket nodes so full knockout trees can be created and wired together programmatically.

- Full knockout bracket generation — the knockout service now constructs a full bracket tree (all rounds) rather than only first-round matches. Placeholder matches for later rounds are created and linked to their source matches (by `source_match_*`); when a match is completed the system will auto-populate winners/losers into the next round using the `action_done()` / `_advance_bracket_teams()` logic.

- Round-robin enhancements — the round-robin service now returns explicit per-round pairings, supports `rounds_count` (repeat full cycles), `schedule_by_round` (create a `gameday` per round) and attempts to alternate `male` / `female` fixtures within a round to provide rest. When a `venue` string matches a `federation.venue` record the scheduler will attach `venue_id` and create/find the `gameday` record.

Implementation notes

- Gameday constraints: the `sports_federation_venues` module adds a `gameday_id` on `federation.match` and enforces a constraint preventing teams in the same `category` from playing the same opponent more than once on the same gameday. This prevents repeated pairings inside a single venue/day block.

- Alternation policy: when scheduling by round the scheduler partitions same-gender fixtures and interleaves male/female matches where possible. Mixed-gender fixtures are appended after the alternation. This is a best-effort policy (it preserves determinism but will not re-seed teams).

- Auto-advance: `federation.standing.action_freeze()` triggers any `federation.stage.progression` rules with `auto_advance=True` for the stage/group being frozen — this provides an automated pipeline from computed standings into new stage participants (and is safe-guarded by the progression rule's `state`).

- Venue handling: the `venue` free-text field has been removed from `federation.match`. Use `venue_id` (Many2one to `federation.venue`) instead. The round-robin and knockout wizards accept a venue name string and resolve it to a `federation.venue` record to populate `venue_id` and `gameday_id`.

Testing and coverage

Add unit and integration tests covering the following:

- `federation.stage.progression`: ensure `action_execute()` selects the correct teams across single-group and cross-group rules and that `seeding_method` options behave as documented.
- `federation.tournament.template`: applying a template creates the expected stages, groups and progression rules.
- Round-robin scheduling: `rounds_count`, `schedule_by_round`, per-round gameday creation, alternation of male/female fixtures, and repeat cycles.
- Knockout bracket generation: bracket size determination, bye handling, and automatic wiring of placeholder matches and advancement on `action_done()`.
- Gameday constraints: enforce no duplicate same-category pairings on a gameday.

# Sports Federation — Technical Note

Last updated: 2026-04-07

This technical note documents architecture, coding conventions, workflows, and extension points for the Sports Federation Odoo 19 custom addons collection located in the `odoo/` folder. It is intended for developers, integrators, and release engineers working on federation features: tournaments, matches, rosters, refereeing, results pipelines, and public website publication.

## Table of contents

- Executive summary
- High-level architecture and module responsibilities
- Data model conventions and patterns
- Workflows and state machines (tournament lifecycle, match-day, result pipeline)
- Competition engine — algorithms, wizards, and deterministic behaviours
- Controllers, portal, and public site patterns
- Security model and record rules
- Performance, scaling and operational concerns
- Testing, CI and quality gates
- Upgrade, migrations and deployment notes
- Developer workflow: how to add models, wizards, views, and tests
- Examples and reference snippets

## Executive summary

The project is a modular suite of Odoo 19 addons implementing a sports federation management system. Modules are intentionally small and focused: `sports_federation_base` owns master data (clubs, teams, seasons), `sports_federation_tournament` implements tournament structure and match records, and `sports_federation_competition_engine` contains deterministic scheduling algorithms and wizards. Domain features (`people`, `rosters`, `officiating`, `result_control`, `standings`, `public_site`, `reporting`) extend core behaviour without mixing responsibilities.

Design goals

- Keep modules decoupled and installable independently where practical.
- Encode business logic in computed models and service/wizard classes rather than ad-hoc scripts.
- Enforce separation of duties via groups and record rules (submit/verify/approve in the result pipeline).
- Make scheduling deterministic and testable (repeatable outputs from the same inputs).

## High-level architecture and module responsibilities

- `sports_federation_base` — Master data: `federation.club`, `federation.team`, `federation.season`, `federation.season.registration`. Ownership of base security groups and global menus. Holds common `ir.sequence` definitions.
- `sports_federation_tournament` — Tournament structure: `federation.competition`, `federation.tournament`, `federation.tournament.stage`, `federation.group`, `federation.tournament.participant`, and `federation.match`. Implements match lifecycle and basic match behaviour.
- `sports_federation_competition_engine` — Service layer for schedule/fixture generation (round-robin, knockout), and helper algorithms. Prefer stateless services and transient wizard models here.
- `sports_federation_people` — Player and license models used for eligibility checks and rosters.
- `sports_federation_rosters` — Season rosters and match sheet management.
- `sports_federation_officiating` — Referee registry and assignment workflows.
- `sports_federation_result_control` — Result submission, verification, approval, contest and correction flows.
- `sports_federation_standings` — Standings computation, tie-break logic, and publishing controls.
- `sports_federation_public_site` / `sports_federation_portal` — Website and portal layers for public pages and club self-service.

Inter-module rules

- Use `depends` in `__manifest__.py` for compile-time coupling and prefer runtime loose coupling in service code.
- Avoid importing models directly across modules in shared utils; reference them through the ORM (`env['federation.model']`).

## Data model conventions and patterns

- Names: all domain models use the `federation.` prefix.
- Fields: prefer explicit names (`home_score`, `away_score`, `match_date`, `venue_id`). Use `_id` for Many2one fields.
- Sequences: centralize `ir.sequence` definitions under the modules that issue numbers (licenses, registrations, match references).
- States: encode lifecycle using `state` selection fields. Implement transition methods (e.g., `action_confirm()`) that include invariant checks and post-transition side-effects (message_post, cron triggers).
- Constraints and indexes: use `_sql_constraints` for DB-level uniqueness and `index=True` on frequently filtered fields.

ORM best practices

- Use `@api.depends` for computed fields; mark heavy computed fields with `store=True` when the value is frequently filtered or sorted.
- Use `read_group` for group-by aggregations instead of computing aggregates in Python loops.
- When creating many records (e.g., fixtures for a large tournament), batch creations in transactions and avoid per-record flushes where possible.

## Workflows and state machines

The canonical workflows live in `odoo/_workflows` (authoritative). Implementation notes below reflect the codebase expectations.

Tournament lifecycle

- States: `draft → open → in_progress → closed | cancelled`.
- Preconditions for `open`: participants registered/confirmed, ruleset assigned, optional venues configured.
- Schedule creation typically moves the tournament to `in_progress` (explicit action required).

Match lifecycle and match-day operations

- States: `draft → scheduled → in_progress → done | cancelled`.
- Pre-match checks: both teams have confirmed match-sheets, required referee roles filled and confirmed, no suspensions on selected players, venue confirmed.
- During match: record events (substitutions, cards) which feed the discipline and finance modules.

Result pipeline

- States: `not_submitted → submitted → verified → approved` (exceptions: `contested`, `corrected`).
- Permissions: separate groups for submit/verify/approve to enforce audit and separation of duties.
- Approved results are the only ones included in official standings computations.

## Competition engine — algorithms and wizards

Principles

- Determinism: given the same input (participant list, seeding, start datetime) the schedule generation must produce the same fixtures. Sort input participants by an unambiguous key (id or explicit seeding) before generation.
- Testability: isolate algorithms in service classes and unit-test them with small deterministic datasets.

Round-robin (circle method)

- Supports odd/even participant counts (auto bye round for odd counts) and single/double round-robin.
- Complexity: O(n^2) matches for n participants (n*(n-1)/2 for single round-robin).

Example pseudocode (circle method)

```python
def generate_round_robin(participants, double=False):
    participants = sorted(participants, key=lambda p: p.seeding or p.id)
    if len(participants) % 2 == 1:
        participants.append(None)  # bye
    n = len(participants)
    rounds = []
    for r in range(n - 1):
        pairs = []
        for i in range(n // 2):
            a = participants[i]
            b = participants[n - 1 - i]
            if a is not None and b is not None:
                pairs.append((a, b))
        rounds.append(pairs)
        participants = [participants[0]] + participants[-1:] + participants[1:-1]
    if double:
        return rounds + [reverse_pairs(r) for r in rounds]
    return rounds
```

Knockout bracket generation

- Seeding strategies: `natural` (order of participants) and `power_of_two` (map to nearest bracket size and set byes).
- Ensure bracket seeding is deterministic and documented in the UI.

Wizards

- Wizards (transient models under `wizards/`) do validations, produce a `summary` preview, and require explicit confirmation to persist matches. They must not perform destructive replacements unless the user explicitly enables `overwrite`.

## Controllers, portal, and public site patterns

Portal patterns

- Use a dedicated `federation.club.representative` model to map `res.users` → `federation.club` for portal ownership and record rules.
- Controllers must perform ownership validation (`_get_clubs_for_user()`) before writes. Record rules are enforcement, controllers are defense-in-depth.

Public site

- Public controllers use `auth='public'` and `sudo()` for reads. Only expose non-sensitive fields (no emails/phones/notes) to public templates.
- Enforce `website_published` and the relevant visibility toggle (`show_public_results`, `show_public_standings`) before serving direct public routes.
- Render public rich text through sanitized website field rendering rather than raw `t-raw` output.

CSRF and forms

- All POST forms must include `csrf_token` and controllers must validate it.

## Security model and record rules

Key principles

- Least privilege: create narrowly-scoped groups and map CRUD rights in `security/ir.model.access.csv`.
- Record rules: express row-level ownership using domains (e.g., `('club_id','in', user.representative_ids.mapped('club_id').ids)`).
- Avoid uncontrolled `sudo()` on write operations.

Groups and separation of duties

- Federation Staff (submit results)
- Result Verifier (verify submitted results)
- Result Approver (approve verified results)
- Referee Coordinator (assign referees)
- Portal Club Representative (portal users)

## Performance, scaling and operational concerns

Large tournaments and match volumes

- Match generation: create matches in batches using `create()` on list-of-dicts to minimize ORM overhead. Consider raw SQL insert for extremely large volumes but keep referential integrity and Odoo cache considerations in mind.
- Indexes: ensure `tournament_id`, `stage_id`, `group_id`, `match_date`, and `state` fields are indexed.
- Aggregation: compute standings incrementally or via nightly cron for large datasets. Prefer `read_group` for real-time small aggregate queries.

Background and asynchronous work

- Use `ir.cron` for scheduled recomputes. For heavy parallel work consider `queue_job` or an external worker queue.

Memory and worker tuning

- For large batch jobs run them on a dedicated worker with increased memory limits and tuned `limit_time_cpu` and `limit_time_real` values.

## Testing, CI and quality gates

Test types

- Unit tests: service classes and algorithms (no DB or minimal mock DB). Keep these fast and deterministic.
- Integration tests: Odoo testcases exercising ORM-level behaviour and workflows.
- Functional tests: simulate portal and public flows (controller-level) when needed.

CI recommendations

- Run module tests in CI and fail PRs on test regressions.
- Include a lint step (flake8/black for Python where applicable) and XML/manifest validation.
- The repository CI entrypoint is `ci/run_tests.sh`; the GitHub workflow at `.github/workflows/ci.yml` reuses that script and runs Black/Flake8 from `requirements.txt`.
- Do not commit runtime credentials. Keep local CI values in `ci/.env`, commit only `ci/.env.example`, and let CI generate ephemeral values at runtime.
- Integration environment variables: maintain `ci/integrations.env.example` with the common external-integration keys (SMTP, SendGrid/Mailgun keys, OAuth client IDs/secrets, Slack webhook, Twilio credentials, AWS S3 keys). Keep real values out of VCS and populate `ci/.env` locally or via your secret store in CI runs.

Example test command

```bash
bash ./ci/run_tests.sh --module sports_federation_competition_engine
```

## Upgrade, migrations and deployment notes

Manifest and data maintenance

- Keep `__manifest__.py` `version` and `data` accurate. Prefer small, focused upgrade scripts to large one-off DB migrations.
- For breaking model changes provide a dedicated migration script (`openupgrade` style) and document steps.

Pre/post hooks

- Use `pre_init_hook` and `post_init_hook` (registered in `__manifest__`) for data transformations where required. Keep hooks idempotent and well-tested.

Backups and rollback

- Always perform full DB and filestore backups prior to upgrades. Test restore paths in your staging environment.

## Developer workflow: add/modify checklist

When introducing a new feature follow this minimal patch checklist:

1. Add model code: `models/<file>.py`. Export in `models/__init__.py`.
2. Add `security/ir.model.access.csv` and any `security/*.xml` record rules.
3. Add views: tree/form/search under `views/*.xml` and register in `__manifest__.py` `data`.
4. Add sequences/data seeds under `data/*.xml`.
5. Write tests under `tests/` covering the main business rule.
6. Update module `README.md` with short usage notes.
7. Run tests locally; run `odoo-bin -d <db> -i <module> --test-enable`.
8. Keep `STATE_AND_OWNERSHIP_MATRIX.md` aligned with any lifecycle or portal-ownership change.

PR checklist (required)

- Tests included and passing
- `security/ir.model.access.csv` updated
- `__manifest__.py` updated (if needed)
- Documentation/README updated
- Small, focused commits and descriptive PR message

## Examples and reference snippets

Wizard skeleton (python)

```python
class FederationRoundRobinWizard(models.TransientModel):
    _name = 'federation.round.robin.wizard'
    _description = 'Round Robin Schedule Wizard'

    tournament_id = fields.Many2one('federation.tournament', required=True)
    use_all_participants = fields.Boolean(default=True)
    summary = fields.Text(compute='_compute_summary')

    def action_generate(self):
        service = RoundRobinService(self.tournament_id)
        schedule = service.generate()
        # create matches in batches
        match_vals = []
        for round in schedule:
            for a, b in round:
                match_vals.append({
                    'tournament_id': self.tournament_id.id,
                    'home_team_id': a.id,
                    'away_team_id': b.id,
                    'state': 'scheduled',
                })
        self.env['federation.match'].create(match_vals)

```

SQL constraints example (in model):

```python
_sql_constraints = [
    ('unique_match_participants', 'UNIQUE(tournament_id, home_team_id, away_team_id, match_date)', 'Duplicate match')
]
```

## Observability and logging

- Use named loggers: `logger = logging.getLogger(__name__)` and log at appropriate levels (INFO for normal milestones, WARNING for recoverable issues, ERROR for exceptions).
- Use `message_post` on records for an audit trail of user-driven state changes.

## Security reminders

- Avoid using `sudo()` to bypass authorization for write operations. If `sudo()` is necessary (controller reading public data), restrict fields returned and validate inputs carefully.

---

Related docs and entry points

- High-level context: [odoo/CONTEXT.md](odoo/CONTEXT.md#L1)
- Workflows (authoritative): [odoo/_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md](odoo/_workflows/WORKFLOW_TOURNAMENT_LIFECYCLE.md#L1), [odoo/_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md](odoo/_workflows/WORKFLOW_MATCH_DAY_OPERATIONS.md#L1), [odoo/_workflows/WORKFLOW_RESULT_PIPELINE.md](odoo/_workflows/WORKFLOW_RESULT_PIPELINE.md#L1)
- Competition engine README: [odoo/sports_federation_competition_engine/README.md](odoo/sports_federation_competition_engine/README.md#L1)

If you'd like, I can now: (1) open a PR draft for this change, (2) run a repo scan of `README` and `INSTALL_LOG` files and fold additional implementation notes into this document, or (3) run the tests for a selected module to validate there are no immediate regressions.
