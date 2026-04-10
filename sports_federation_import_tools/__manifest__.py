{
    "name": "Sports Federation Import Tools",
    "version": "19.0.1.1.0",
    "category": "Sports",
    "summary": "Wizard-driven CSV import tools for clubs, seasons, teams, players, and tournament participants",
    "description": "CSV import wizards with dry-run validation, mapping guidance, and duplicate-safe onboarding for clubs, seasons, teams, players, and tournament participants.",
    "author": "Sports Federation",
    "website": "",
    "license": "LGPL-3",
    "depends": [
        "sports_federation_base",
        "sports_federation_people",
        "sports_federation_tournament",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/import_wizard_views.xml",
        "views/menu_views.xml",
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
    "sequence": 60,
}