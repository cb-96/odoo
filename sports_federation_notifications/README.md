# Sports Federation Notifications

Centralised notification helpers, email templates, and scheduled reminders.
Provides a reusable service layer for sending emails and creating activities,
with a log of all notifications sent.

## Purpose

Gives other modules a **single entry point** for sending notifications. Instead
of each module implementing its own mail logic, they call the notification
service, which handles template rendering, sending, and logging.

## Dependencies

| Module | Reason |
|--------|--------|
| `sports_federation_base` | Core entities |
| `sports_federation_people` | Player/person context |
| `sports_federation_tournament` | Tournament context |
| `sports_federation_portal` | Portal context |
| `mail` | Email engine |

## Models

### `federation.notification.log`

Audit record of every notification sent through the federation.

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Notification title |
| `target_model` / `target_res_id` | Char / Integer | What record triggered it |
| `recipient_partner_id` | Many2one | Recipient partner |
| `recipient_email` | Char | Recipient email address |
| `notification_type` | Selection | email / activity / other |
| `template_xmlid` | Char | Which template was used |
| `sent_on` | Datetime | When sent |
| `state` | Selection | pending / sent / failed |
| `message` | Text | Content or error details |

### `federation.notification.service` (AbstractModel)

Reusable service methods callable by any module.

| Method | Description |
|--------|-------------|
| `send_email_template(record, template_xmlid, ...)` | Send an email using a mail.template and log it |
| `create_activity(record, activity_type_xmlid, ...)` | Create a mail.activity and log it |
| `_cron_placeholder_notification_scan()` | Scheduled scan for overdue draft registrations |

## Data Files

| File | Content |
|------|---------|
| `data/mail_templates.xml` | Generic contact, registration reminder, missing data notice templates |
| `data/ir_cron.xml` | Daily notification scan scheduled action (inactive by default) |

## Key Behaviours

1. **Service pattern** — AbstractModel with helper methods; no table, just logic.
2. **Comprehensive logging** — Every send/activity creation produces a log entry.
3. **QWeb templates** — Email templates use Odoo 19 QWeb syntax (`<t t-out=""/>`).
4. **Scheduled scan** — Cron job detects stale draft registrations and logs reminders.
