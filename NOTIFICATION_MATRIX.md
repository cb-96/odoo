# Notification Matrix

This document defines **who receives what notification** and **when** for
the Sports Federation Platform.  It is the authoritative contract between
the business domain modules (tournament, result_control, finance_bridge,
people) and the notification dispatcher in
`sports_federation_notifications`.

---

## Trigger Matrix

| Event | Trigger Model / Action | Recipients | Notification Type | Template XML ID | Implemented? |
|---|---|---|---|---|---|
| Tournament published | `federation.tournament.website_published = True` | All registered club managers | Email | `sports_federation_notifications.mail_tournament_published` | Stub |
| Participant registration confirmed | `federation.tournament.participant.action_confirm()` | Club contact + team captain | Email | `sports_federation_notifications.mail_participant_confirmed` | Stub |
| Match result submitted | `federation.match.action_submit_result()` | Federation verifier group | Activity | — | Stub |
| Match result approved | `federation.match.action_approve_result()` | Home club + away club contacts | Email | `sports_federation_notifications.mail_result_approved` | Stub |
| Match result contested | `federation.match.action_contest_result()` | Home club + away club + federation manager | Email | `sports_federation_notifications.mail_result_contested` | Stub |
| Standing frozen | `federation.standing.action_freeze()` | All tournament participants | Email | `sports_federation_notifications.mail_standing_frozen` | Stub |
| Finance event confirmed | `federation.finance.event.action_confirm()` | Club contact / player / referee | Email | `sports_federation_notifications.mail_finance_confirmed` | Stub |
| Referee assigned to match | `federation.match.referee.create()` | Referee | Email | `sports_federation_notifications.mail_referee_assigned` | Stub |
| Referee confirmation overdue | `federation.notification.service._cron_placeholder_notification_scan()` | Federation staff | Activity | — | Stub |
| Match officiating shortage | `federation.notification.service._cron_placeholder_notification_scan()` | Federation staff | Activity | — | Stub |
| Suspension issued | `federation.suspension.action_issue()` | Player + club contact | Email | `sports_federation_notifications.mail_suspension_issued` | Stub |

---

## Dispatcher Architecture

The dispatcher is implemented as an **AbstractModel** inheriting the
`federation.notification.service` mixin, adding methods for each trigger
event above.  Concrete modules (tournament, result_control, etc.) call these
methods at the appropriate points in their lifecycle methods.

```
federation.notification.dispatcher (AbstractModel)
    │── send_tournament_published(tournament)
    │── send_participant_confirmed(participant)
    │── send_result_submitted(match)
    │── send_result_approved(match)
    │── send_result_contested(match)
    │── send_standing_frozen(standing)
    │── send_finance_event_confirmed(finance_event)
    │── send_referee_assigned(match_officiating)
    │── send_referee_confirmation_overdue(match_officiating)
    │── send_referee_shortage_alert(match)
    └── send_suspension_issued(suspension)
```

Each method:
1. Checks whether the relevant module is installed (guard via `env.get()`).
2. Resolves recipient partners.
3. Calls `self.send_email_template()` or `self.create_activity()` from the
   base `federation.notification.service`.
4. Returns the `federation.notification.log` record.

---

## Implementation Status

Stubs are defined in
`sports_federation_notifications/models/notification_dispatcher.py`.
Each method currently logs a placeholder entry.  Fill in the template XML ID
and recipient resolution as the corresponding modules stabilize.

---

## Error Handling

All dispatcher methods must be non-blocking:
- Use `try/except` around actual sending so a notification failure never
  rolls back a business transaction.
- On failure, set log state to `failed` and record the exception message.
- Never raise `ValidationError` from a dispatcher method.

---

_Last updated: Phase 2 automation (auto-generated) — update this file when new triggers are added._
