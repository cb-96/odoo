from odoo import fields, models


class FederationTournament(models.Model):
    _inherit = "federation.tournament"

    website_published = fields.Boolean(
        string="Published on Website",
        default=False,
    )
    public_description = fields.Html(
        string="Public Description",
    )
    public_slug = fields.Char(
        string="Public Slug",
        help="Optional SEO/public URL slug override",
    )
    show_public_results = fields.Boolean(
        string="Show Public Results",
        default=True,
    )
    show_public_standings = fields.Boolean(
        string="Show Public Standings",
        default=True,
    )

    def can_access_public_detail(self):
        self.ensure_one()
        return bool(self.website_published)

    def can_access_public_results(self):
        self.ensure_one()
        return bool(self.can_access_public_detail() and self.show_public_results)

    def can_access_public_standings(self):
        self.ensure_one()
        return bool(self.can_access_public_detail() and self.show_public_standings)


class FederationStanding(models.Model):
    _inherit = "federation.standing"

    website_published = fields.Boolean(
        string="Published on Website",
        default=False,
    )
    public_title = fields.Char(
        string="Public Title",
    )