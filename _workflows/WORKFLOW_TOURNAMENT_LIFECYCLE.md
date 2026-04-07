# Workflow: Tournament Lifecycle

Full lifecycle of a tournament — from competition definition and participant
enrolment through schedule generation, match execution, and final completion.

## Overview

A **competition** is a recurring series (e.g. "National League Division 1").
Within each season, competitions host one or more **tournaments** which are
structured into stages, groups, and matches. This workflow covers the entire
journey from initial setup to final completion.

## Modules Involved

| Module | Role |
|--------|------|
| `sports_federation_base` | Seasons, clubs, teams |
| `sports_federation_rules` | Rule sets governing scoring, tie-breaks, eligibility |
| `sports_federation_tournament` | Competition, tournament, stage, group, participant, match models |
| `sports_federation_competition_engine` | Round-robin and knockout schedule generation wizards |
| `sports_federation_venues` | Venue and playing-area assignment |
| `sports_federation_standings` | Standings computation at each stage |
| `sports_federation_public_site` | Public publication of tournament pages |

## Step-by-Step Flow

### 1. Competition Setup

**Actor**: Federation administrator
**Module**: `sports_federation_rules`, `sports_federation_tournament`

1. Define a **rule set** with scoring values (win/draw/loss points), tie-break
   criteria, squad-size limits, and eligibility rules.
2. Create a **competition** (e.g. "National League Division 1").
3. Link the competition to the active season and the rule set.
4. Set competition state to `active`.

### 2. Tournament Creation

**Actor**: Federation administrator
**Module**: `sports_federation_tournament`

1. Under the competition, create a **tournament** (e.g. "NL Div 1 — Season 2025").
2. Set tournament type: `league`, `cup`, `friendly`, or `playoff`.
3. Assign date range, rule set (inherited from competition or overridden).
4. Set maximum participants if applicable.
5. Tournament starts in `draft` state.

### 3. Venue Assignment

**Actor**: Federation administrator
**Module**: `sports_federation_venues`

1. Create or select venues with address, capacity, and playing areas.
2. Link venues to the tournament via the `venues` Many2many field.
3. Individual matches can later reference specific venues and playing areas.

### 4. Participant Enrolment

**Actor**: Federation administrator (or via import)
**Module**: `sports_federation_tournament`, `sports_federation_import_tools`

1. Add **participants** to the tournament — each links a team to the tournament.
2. Optionally assign participants to specific stages and groups.
3. Set seeding ranks for bracket placement.
4. Participant states: `registered` → `confirmed` → `withdrawn` / `eliminated`.
5. Move tournament to `open` state once enrolment is complete.

Bulk enrolment is available via the **Import Tournament Participants** wizard.

### 5. Stage & Group Structure

**Actor**: Federation administrator
**Module**: `sports_federation_tournament`

1. Create **stages** within the tournament (e.g. "Group Phase", "Quarter-Finals").
2. Set stage type: `group`, `knockout`, `playoff`, or `other`.
3. Order stages by sequence.
4. Within each stage, create **groups** (e.g. "Group A", "Pool 1").
5. Assign participants to groups.

### 6. Schedule Generation

**Actor**: Federation administrator
**Module**: `sports_federation_competition_engine`

1. Move tournament to `in_progress` state.
2. Open the **Round Robin Wizard** or **Knockout Wizard** from the tournament form.
3. Configure: select participants, set start date/time, interval between rounds,
   default venue.
4. Preview the generated schedule via the summary field.
5. Confirm to create all match records automatically.

**Round Robin**: Circle method generates a complete schedule where every team plays
every other team once (single) or twice (double).

**Knockout**: Seeded single-elimination bracket with automatic byes for non-power-of-two counts.

### 7. Match Execution

**Actor**: Federation staff, referees
**Module**: `sports_federation_tournament`

1. Matches are scheduled with date/time, venue, home/away teams.
2. Match states progress: `draft` → `scheduled` → `in_progress` → `completed`.
3. Scores are entered on the match form (home_score, away_score).
4. Match-day details are handled by the [Match Day Operations](WORKFLOW_MATCH_DAY_OPERATIONS.md)
   workflow.

### 8. Standings Computation

**Actor**: Federation administrator
**Module**: `sports_federation_standings`

1. Create a **standings** record scoped to the tournament, stage, or group.
2. Link the rule set for scoring and tie-break rules.
3. Compute standings: aggregates match results into ranked lines.
4. States: `draft` → `computed` → `published`.
5. Publish to make visible on the public site.

### 9. Stage Progression

**Actor**: Federation administrator
**Module**: `sports_federation_tournament`

1. After a stage completes, review standings to determine qualifiers.
2. Qualification rules from the rule set indicate who advances.
3. Create participants in the next stage (e.g. move group winners to knockout).
4. Generate the next stage's schedule using competition engine wizards.

### 10. Tournament Completion

**Actor**: Federation administrator
**Module**: `sports_federation_tournament`

1. After the final stage, review and approve all remaining results.
2. Compute and publish final standings.
3. Set tournament state to `completed`.
4. Competition can be closed at end of season.

### 11. Public Publication

**Actor**: Federation administrator
**Module**: `sports_federation_public_site`

1. Set `website_published = True` on the tournament.
2. Configure public slug, description, and toggle results/standings visibility.
3. Publish standings records.
4. Public pages become available at `/competitions/<slug>`.

## State Diagram

```
Competition: draft → active → closed

Tournament: draft → open → in_progress → completed
                                       → cancelled

Match: draft → scheduled → in_progress → completed
                                        → cancelled

Standings: draft → computed → published

Participant: registered → confirmed → withdrawn
                                    → eliminated
```

## Key Decision Points

| Question | Outcome |
|----------|---------|
| League or Cup format? | Determines round-robin vs. knockout wizard |
| How many stages? | Single-stage league or multi-stage tournament with progression |
| Power-of-two bracket? | Knockout wizard handles byes for odd counts |
| When to publish? | Standings should be computed and verified before publication |

## Related Workflows

- [Match Day Operations](WORKFLOW_MATCH_DAY_OPERATIONS.md) — detailed match-day process
- [Result Pipeline](WORKFLOW_RESULT_PIPELINE.md) — score verification and approval
- [Season Registration](WORKFLOW_SEASON_REGISTRATION.md) — prerequisite club/team registration
