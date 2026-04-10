"""
Notification Dispatcher — event-driven notification stubs.

Each method here maps to one row in ``odoo/NOTIFICATION_MATRIX.md``.
Methods are currently stubs that log a placeholder entry.  To activate a
notification, replace the placeholder ``Log.create(...)`` call with actual
``send_email_template`` or ``create_activity`` calls once the mail templates
are authored.

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
        """Notify registered club managers when a tournament is published.

        TODO: resolve recipient list from ``federation.season.registration``
        and use ``sports_federation_notifications.mail_tournament_published``.
        """
        Log = self.env["federation.notification.log"]
        try:
            Log.create({
                "name": f"[stub] Tournament published: {tournament.name}",
                "target_model": "federation.tournament",
                "target_res_id": tournament.id,
                "notification_type": "email",
                "state": "sent",
                "sent_on": fields.Datetime.now(),
                "message": "Dispatcher stub — no email template configured yet.",
            })
        except Exception as exc:
            Log.create({
                "name": f"[error] Tournament published: {tournament.name}",
                "target_model": "federation.tournament",
                "target_res_id": tournament.id,
                "notification_type": "email",
                "state": "failed",
                "message": str(exc),
            })

    # ------------------------------------------------------------------
    # Participant events
    # ------------------------------------------------------------------

    def send_participant_confirmed(self, participant):
        """Notify club contact when a tournament participant is confirmed.

        TODO: template ``sports_federation_notifications.mail_participant_confirmed``.
        """
        Log = self.env["federation.notification.log"]
        try:
            Log.create({
                "name": f"[stub] Participant confirmed: {participant.name}",
                "target_model": "federation.tournament.participant",
                "target_res_id": participant.id,
                "notification_type": "email",
                "state": "sent",
                "sent_on": fields.Datetime.now(),
                "message": "Dispatcher stub — no email template configured yet.",
            })
        except Exception as exc:
            Log.create({
                "name": f"[error] Participant confirmed: {participant.name}",
                "target_model": "federation.tournament.participant",
                "target_res_id": participant.id,
                "notification_type": "email",
                "state": "failed",
                "message": str(exc),
            })

    # ------------------------------------------------------------------
    # Match result events
    # ------------------------------------------------------------------

    def send_result_submitted(self, match):
        """Create an activity for verifiers when a match result is submitted.

        TODO: use ``create_activity`` targeting the verifier group representative.
        """
        Log = self.env["federation.notification.log"]
        try:
            Log.create({
                "name": f"[stub] Result submitted: {match.name}",
                "target_model": "federation.match",
                "target_res_id": match.id,
                "notification_type": "activity",
                "state": "sent",
                "sent_on": fields.Datetime.now(),
                "message": "Dispatcher stub — no activity wired yet.",
            })
        except Exception as exc:
            Log.create({
                "name": f"[error] Result submitted: {match.name}",
                "target_model": "federation.match",
                "target_res_id": match.id,
                "notification_type": "activity",
                "state": "failed",
                "message": str(exc),
            })

    def send_result_approved(self, match):
        """Email both clubs when a result is officially approved.

        TODO: template ``sports_federation_notifications.mail_result_approved``
        with recipients: home_club.partner_id and away_club.partner_id.
        """
        Log = self.env["federation.notification.log"]
        try:
            Log.create({
                "name": f"[stub] Result approved: {match.name}",
                "target_model": "federation.match",
                "target_res_id": match.id,
                "notification_type": "email",
                "state": "sent",
                "sent_on": fields.Datetime.now(),
                "message": "Dispatcher stub — no email template configured yet.",
            })
        except Exception as exc:
            Log.create({
                "name": f"[error] Result approved: {match.name}",
                "target_model": "federation.match",
                "target_res_id": match.id,
                "notification_type": "email",
                "state": "failed",
                "message": str(exc),
            })

    def send_result_contested(self, match):
        """Email clubs and federation manager when a result is contested.

        TODO: template ``sports_federation_notifications.mail_result_contested``.
        """
        Log = self.env["federation.notification.log"]
        try:
            Log.create({
                "name": f"[stub] Result contested: {match.name}",
                "target_model": "federation.match",
                "target_res_id": match.id,
                "notification_type": "email",
                "state": "sent",
                "sent_on": fields.Datetime.now(),
                "message": "Dispatcher stub — no email template configured yet.",
            })
        except Exception as exc:
            Log.create({
                "name": f"[error] Result contested: {match.name}",
                "target_model": "federation.match",
                "target_res_id": match.id,
                "notification_type": "email",
                "state": "failed",
                "message": str(exc),
            })

    # ------------------------------------------------------------------
    # Standings events
    # ------------------------------------------------------------------

    def send_standing_frozen(self, standing):
        """Notify participants when a standing is frozen.

        TODO: template ``sports_federation_notifications.mail_standing_frozen``
        with recipients derived from ``standing.tournament_id.participant_ids``.
        """
        Log = self.env["federation.notification.log"]
        try:
            Log.create({
                "name": f"[stub] Standing frozen: {standing.name}",
                "target_model": "federation.standing",
                "target_res_id": standing.id,
                "notification_type": "email",
                "state": "sent",
                "sent_on": fields.Datetime.now(),
                "message": "Dispatcher stub — no email template configured yet.",
            })
        except Exception as exc:
            Log.create({
                "name": f"[error] Standing frozen: {standing.name}",
                "target_model": "federation.standing",
                "target_res_id": standing.id,
                "notification_type": "email",
                "state": "failed",
                "message": str(exc),
            })

    # ------------------------------------------------------------------
    # Finance events
    # ------------------------------------------------------------------

    def send_finance_event_confirmed(self, finance_event):
        """Notify the relevant club or person when a finance event is confirmed.

        TODO: template ``sports_federation_notifications.mail_finance_confirmed``;
        resolve recipient from ``finance_event.club_id.partner_id``.
        """
        Log = self.env["federation.notification.log"]
        try:
            Log.create({
                "name": f"[stub] Finance event confirmed: {finance_event.name}",
                "target_model": "federation.finance.event",
                "target_res_id": finance_event.id,
                "notification_type": "email",
                "state": "sent",
                "sent_on": fields.Datetime.now(),
                "message": "Dispatcher stub — no email template configured yet.",
            })
        except Exception as exc:
            Log.create({
                "name": f"[error] Finance event confirmed: {finance_event.name}",
                "target_model": "federation.finance.event",
                "target_res_id": finance_event.id,
                "notification_type": "email",
                "state": "failed",
                "message": str(exc),
            })

    # ------------------------------------------------------------------
    # Officiating events
    # ------------------------------------------------------------------

    def send_referee_assigned(self, match_officiating):
        """Notify a referee when they are assigned to a match.

        TODO: template ``sports_federation_notifications.mail_referee_assigned``
        targeting ``match_officiating.referee_id.partner_id``.
        """
        Log = self.env["federation.notification.log"]
        try:
            name = getattr(match_officiating, "name", str(match_officiating.id))
            Log.create({
                "name": f"[stub] Referee assigned: {name}",
                "target_model": match_officiating._name,
                "target_res_id": match_officiating.id,
                "notification_type": "email",
                "state": "sent",
                "sent_on": fields.Datetime.now(),
                "message": "Dispatcher stub — no email template configured yet.",
            })
        except Exception as exc:
            Log.create({
                "name": "[error] Referee assigned",
                "notification_type": "email",
                "state": "failed",
                "message": str(exc),
            })

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
