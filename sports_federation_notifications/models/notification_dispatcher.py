"""
Notification Dispatcher — event-driven notification routing.

Each method here maps to one row in ``odoo/NOTIFICATION_MATRIX.md`` and
resolves recipients before delegating to ``send_email_template`` or
``create_activity``. Most modeled workflow scenarios are now live; suspension
issuance remains the only placeholder until the discipline template and
recipient mapping are finalized.

Usage (from any model override):
::

    Dispatcher = self.env.get("federation.notification.dispatcher")
    if Dispatcher is not None:
        Dispatcher.send_result_approved(self)
"""
from odoo import fields, models


class FederationNotificationDispatcher(models.AbstractModel):
    """Dispatcher for domain-event driven notifications.

    Inherits the notification service helpers (``send_email_template``,
    ``create_activity``) and adds domain-specific dispatch methods.
    """

    _name = "federation.notification.dispatcher"
    _description = "Federation Notification Dispatcher"
    _inherit = "federation.notification.service"

    def _unique_emails(self, emails):
        unique = []
        for email in emails:
            normalized = (email or "").strip()
            if normalized and normalized not in unique:
                unique.append(normalized)
        return unique

    def _log_missing_recipients(self, record, log_name, notification_type, message):
        return self.env["federation.notification.log"].create({
            "name": log_name,
            "target_model": record._name,
            "target_res_id": record.id,
            "notification_type": notification_type,
            "state": "failed",
            "message": message,
        })

    def _send_email_or_log(self, record, template_xmlid, log_name, emails):
        unique_emails = self._unique_emails(emails)
        if not unique_emails:
            return self._log_missing_recipients(
                record,
                log_name,
                "email",
                "No recipient email available for this notification.",
            )
        return self.send_email_template(
            record,
            template_xmlid,
            email_to=unique_emails,
            log_name=log_name,
        )

    def _create_group_activities(self, record, group_xmlid, summary, note=None):
        group = self.env.ref(group_xmlid, raise_if_not_found=False)
        users = group.users if group else self.env["res.users"].browse([])
        if not users:
            return self._log_missing_recipients(
                record,
                summary,
                "activity",
                f"No users configured in group {group_xmlid}.",
            )

        logs = self.env["federation.notification.log"]
        for user in users:
            logs |= self.create_activity(record, user.id, summary, note=note)
        return logs

    # ------------------------------------------------------------------
    # Season registration events
    # ------------------------------------------------------------------

    def _get_season_registration_recipient(self, registration):
        partner = False
        if "partner_id" in registration._fields and registration.partner_id and registration.partner_id.email:
            partner = registration.partner_id

        email_to = False
        if not partner:
            email_to = registration.club_id.email or False

        return partner, email_to

    def send_season_registration_confirmed(self, registration):
        partner, email_to = self._get_season_registration_recipient(registration)
        return self.send_email_template(
            registration,
            "sports_federation_notifications.template_federation_season_registration_confirmed",
            partner=partner,
            email_to=email_to,
            log_name=f"Season registration confirmed: {registration.name}",
        )

    def send_season_registration_rejected(self, registration):
        partner, email_to = self._get_season_registration_recipient(registration)
        return self.send_email_template(
            registration,
            "sports_federation_notifications.template_federation_season_registration_rejected",
            partner=partner,
            email_to=email_to,
            log_name=f"Season registration rejected: {registration.name}",
        )

    # ------------------------------------------------------------------
    # Tournament events
    # ------------------------------------------------------------------

    def send_tournament_published(self, tournament):
        emails = tournament.participant_ids.mapped("club_id.email") + tournament.participant_ids.mapped("team_id.email")
        return self._send_email_or_log(
            tournament,
            "sports_federation_notifications.template_federation_tournament_published",
            f"Tournament published: {tournament.name}",
            emails,
        )

    # ------------------------------------------------------------------
    # Participant events
    # ------------------------------------------------------------------

    def send_participant_confirmed(self, participant):
        emails = [participant.team_id.email, participant.club_id.email]
        return self._send_email_or_log(
            participant,
            "sports_federation_notifications.template_federation_participant_confirmed",
            f"Participant confirmed: {participant.name}",
            emails,
        )

    # ------------------------------------------------------------------
    # Match result events
    # ------------------------------------------------------------------

    def send_result_submitted(self, match):
        return self._create_group_activities(
            match,
            "sports_federation_result_control.group_result_validator",
            f"Verify result: {match.name}",
            note="A match result has been submitted and awaits verification.",
        )

    def send_result_approved(self, match):
        emails = [
            match.home_team_id.email,
            match.home_team_id.club_id.email,
            match.away_team_id.email,
            match.away_team_id.club_id.email,
        ]
        return self._send_email_or_log(
            match,
            "sports_federation_notifications.template_federation_result_approved",
            f"Result approved: {match.name}",
            emails,
        )

    def send_result_contested(self, match):
        manager_group = self.env.ref(
            "sports_federation_base.group_federation_manager",
            raise_if_not_found=False,
        )
        manager_emails = manager_group.users.mapped("email") if manager_group else []
        emails = [
            match.home_team_id.email,
            match.home_team_id.club_id.email,
            match.away_team_id.email,
            match.away_team_id.club_id.email,
            *manager_emails,
        ]
        return self._send_email_or_log(
            match,
            "sports_federation_notifications.template_federation_result_contested",
            f"Result contested: {match.name}",
            emails,
        )

    # ------------------------------------------------------------------
    # Officiating events
    # ------------------------------------------------------------------

    def send_referee_confirmation_overdue(self, match_officiating):
        return self._create_group_activities(
            match_officiating,
            "sports_federation_base.group_federation_manager",
            f"Referee confirmation overdue: {match_officiating.match_id.name}",
            note=match_officiating.readiness_feedback or "Referee confirmation deadline has been missed.",
        )

    def send_referee_shortage_alert(self, match):
        return self._create_group_activities(
            match,
            "sports_federation_base.group_federation_manager",
            f"Referee shortage: {match.name}",
            note=getattr(match, "official_readiness_issues", False) or "Match is missing required officials.",
        )

    # ------------------------------------------------------------------
    # Standings events
    # ------------------------------------------------------------------

    def send_standing_frozen(self, standing):
        emails = standing.tournament_id.participant_ids.mapped("club_id.email")
        return self._send_email_or_log(
            standing,
            "sports_federation_notifications.template_federation_standing_frozen",
            f"Standing frozen: {standing.name}",
            emails,
        )

    # ------------------------------------------------------------------
    # Finance events
    # ------------------------------------------------------------------

    def send_finance_event_confirmed(self, finance_event):
        emails = [
            finance_event.partner_id.email,
            finance_event.club_id.email,
            finance_event.player_id.email,
            finance_event.referee_id.email,
        ]
        return self._send_email_or_log(
            finance_event,
            "sports_federation_notifications.template_federation_finance_confirmed",
            f"Finance event confirmed: {finance_event.name}",
            emails,
        )

    # ------------------------------------------------------------------
    # Officiating events
    # ------------------------------------------------------------------

    def send_referee_assigned(self, match_officiating):
        return self._send_email_or_log(
            match_officiating,
            "sports_federation_notifications.template_federation_referee_assigned",
            f"Referee assigned: {match_officiating.match_id.name}",
            [match_officiating.referee_id.email],
        )

    # ------------------------------------------------------------------
    # Discipline events
    # ------------------------------------------------------------------

    def send_suspension_issued(self, suspension):
        """Notify the player and club contact when a suspension is issued.

        TODO: template ``sports_federation_notifications.mail_suspension_issued``;
        resolve from ``suspension.player_id.partner_id``.
        """
        Log = self.env["federation.notification.log"]
        try:
            name = getattr(suspension, "name", str(suspension.id))
            Log.create({
                "name": f"[stub] Suspension issued: {name}",
                "target_model": suspension._name,
                "target_res_id": suspension.id,
                "notification_type": "email",
                "state": "sent",
                "sent_on": fields.Datetime.now(),
                "message": "Dispatcher stub — no email template configured yet.",
            })
        except Exception as exc:
            Log.create({
                "name": "[error] Suspension issued",
                "notification_type": "email",
                "state": "failed",
                "message": str(exc),
            })
