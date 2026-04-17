from odoo import api, models
from odoo.exceptions import AccessError


class FederationPortalPrivilege(models.AbstractModel):
    _name = "federation.portal.privilege"
    _description = "Federation Portal Privilege Boundary"

    @api.model
    def elevate(self, records, user=None):
        """Return a recordset or model env elevated for a portal-owned action."""
        user = user or self.env.user
        return records.with_user(user).sudo()

    @api.model
    def portal_create(self, model_env, values, user=None):
        """Create a record through the shared portal privilege boundary."""
        return self.elevate(model_env, user=user).create(values)

    @api.model
    def portal_write(self, records, values, user=None):
        """Write through the shared portal privilege boundary."""
        return self.elevate(records, user=user).write(values)

    @api.model
    def portal_call(self, records, method_name, *args, user=None, **kwargs):
        """Call a record method through the shared portal privilege boundary."""
        return getattr(self.elevate(records, user=user), method_name)(*args, **kwargs)

    @api.model
    def portal_search(self, model_env, domain, user=None, **kwargs):
        """Search through the shared portal privilege boundary."""
        return self.elevate(model_env, user=user).search(domain, **kwargs)

    @api.model
    def portal_search_count(self, model_env, domain, user=None, **kwargs):
        """Count records through the shared portal privilege boundary."""
        return self.elevate(model_env, user=user).search_count(domain, **kwargs)

    @api.model
    def portal_assert_in_domain(self, records, domain, access_message, user=None):
        """Ensure all records are visible inside the expected portal domain."""
        records = records.exists()
        if not records:
            raise AccessError(access_message)

        privileged_records = self.elevate(records, user=user)
        allowed_count = privileged_records.search_count(list(domain) + [("id", "in", records.ids)])
        if allowed_count != len(records):
            raise AccessError(access_message)
        return privileged_records