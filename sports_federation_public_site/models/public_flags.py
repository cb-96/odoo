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


class FederationStanding(models.Model):
    _inherit = "federation.standing"

    website_published = fields.Boolean(
        string="Published on Website",
        default=False,
    )
    public_title = fields.Char(
        string="Public Title",
    )