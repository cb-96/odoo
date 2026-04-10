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
| Season registration confirmed | `federation.season.registration.action_confirm()` | Submitting representative or club contact | Email | `sports_federation_notifications.template_federation_season_registration_confirmed` | Yes |
| Season registration returned to draft | `federation.season.registration.action_reject()` | Submitting representative or club contact | Email | `sports_federation_notifications.template_federation_season_registration_rejected` | Yes |
| Tournament published | `federation.tournament.write({'website_published': True})` | Participant club and team contacts | Email | `sports_federation_notifications.template_federation_tournament_published` | Yes |
| Participant confirmed | `federation.tournament.participant.action_confirm()` | Team contact + club contact | Email | `sports_federation_notifications.template_federation_participant_confirmed` | Yes |
| Match result submitted | `federation.match.action_submit_result()` | Users in result validator group | Activity | — | Yes |
| Match result approved | `federation.match.action_approve_result()` | Home/away team and club contacts | Email | `sports_federation_notifications.template_federation_result_approved` | Yes |
| Match result contested | `federation.match.action_contest_result()` | Home/away team and club contacts + federation managers | Email | `sports_federation_notifications.template_federation_result_contested` | Yes |
| Standing frozen | `federation.standing.action_freeze()` | Tournament participant club contacts | Email | `sports_federation_notifications.template_federation_standing_frozen` | Yes |
| Finance event confirmed | `federation.finance.event.action_confirm()` | Partner or club/player/referee contact | Email | `sports_federation_notifications.template_federation_finance_confirmed` | Yes |
| Referee assigned to match | `federation.match.referee.create()` | Referee | Email | `sports_federation_notifications.template_federation_referee_assigned` | Yes |
| Referee confirmation overdue | `federation.notification.service._cron_placeholder_notification_scan()` | Federation managers | Activity | — | Yes |
| Match officiating shortage | `federation.notification.service._cron_placeholder_notification_scan()` | Federation managers | Activity | — | Yes |
| Suspension issued | `federation.suspension.action_issue()` | Player + club contact | Email | — | No |

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
1. Resolves recipient emails or target user groups from the business record.
2. Delegates to `self.send_email_template()` or `self.create_activity()` from the
  base `federation.notification.service`.
3. Returns one or more `federation.notification.log` records capturing sent or failed delivery.

---

## Implementation Status

The dispatcher is live for the high-value workflow scenarios above. Email-based
events create sent or failed log rows through the shared notification service,
and activity-based events create one log row per assigned user. The only
remaining stub is `send_suspension_issued()`.

---

## Error Handling

All dispatcher methods must be non-blocking:
- Use `try/except` around actual sending so a notification failure never
  rolls back a business transaction.
- On failure, set log state to `failed` and record the exception message.
- Never raise `ValidationError` from a dispatcher method.

---

_Last updated: 2026-04-10 — update this file when new triggers are added._
