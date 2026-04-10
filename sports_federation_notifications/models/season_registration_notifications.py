from odoo import models


class FederationSeasonRegistrationNotifications(models.Model):
    _inherit = "federation.season.registration"

    def action_confirm(self):
        result = super().action_confirm()
        dispatcher = self.env.get("federation.notification.dispatcher")
        if dispatcher:
            for registration in self.filtered(lambda rec: rec.state == "confirmed"):
                dispatcher.send_season_registration_confirmed(registration)
        return result

    def action_reject(self, reason=None):
        submitted_registrations = self.filtered(lambda rec: rec.state == "submitted")
        result = super().action_reject(reason=reason)
        dispatcher = self.env.get("federation.notification.dispatcher")
        if dispatcher:
            for registration in submitted_registrations.filtered(lambda rec: rec.state == "draft"):
                dispatcher.send_season_registration_rejected(registration)
        return result