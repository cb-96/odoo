from odoo import _, api, models
from odoo.exceptions import AccessError, ValidationError


class FederationMatchSheet(models.Model):
    _inherit = "federation.match.sheet"

    @api.model
    def _portal_get_domain(self, user=None):
        """Handle the portal-specific get domain flow."""
        user = user or self.env.user
        club_scope = user.portal_club_scope_ids
        team_scope = user.portal_team_scope_ids
        if team_scope and club_scope:
            return ["|", ("team_id", "in", team_scope.ids), ("team_id.club_id", "in", club_scope.ids)]
        if team_scope:
            return [("team_id", "in", team_scope.ids)]
        represented_clubs = user.represented_club_ids
        if represented_clubs:
            return [("team_id.club_id", "in", represented_clubs.ids)]
        return [("id", "=", False)]

    def _portal_assert_review_access(self, user=None):
        """Handle the portal-specific assert review access flow."""
        user = user or self.env.user
        domain = self._portal_get_domain(user=user)
        if domain == [("id", "=", False)]:
            raise AccessError(_("You do not have portal access to match sheets."))
        self.env["federation.portal.privilege"].portal_assert_in_domain(
            self,
            domain,
            _("You can only review match sheets for your assigned teams or club."),
            user=user,
        )
        return True

    def _portal_update_preparation(self, values=None, user=None):
        """Handle the portal-specific update preparation flow."""
        user = user or self.env.user
        self._portal_assert_review_access(user=user)
        locked = self.filtered(lambda sheet: sheet.state == "locked")
        if locked:
            raise ValidationError(_("Locked match sheets cannot be updated from the portal."))
        values = values or {}
        prepared = {}
        if "coach_name" in values:
            prepared["coach_name"] = (values.get("coach_name") or "").strip() or False
        if "manager_name" in values:
            prepared["manager_name"] = (values.get("manager_name") or "").strip() or False
        if "notes" in values:
            prepared["notes"] = (values.get("notes") or "").strip() or False
        if prepared:
            self.env["federation.portal.privilege"].portal_write(
                self,
                prepared,
                user=user,
            )
        return True

    def _portal_action_submit(self, user=None):
        """Handle the portal-specific action submit flow."""
        user = user or self.env.user
        self._portal_assert_review_access(user=user)
        drafts = self.filtered(lambda sheet: sheet.state == "draft")
        if not drafts:
            raise ValidationError(_("Only draft match sheets can be submitted from the portal."))
        return self.env["federation.portal.privilege"].portal_call(
            drafts,
            "action_submit",
            user=user,
        )