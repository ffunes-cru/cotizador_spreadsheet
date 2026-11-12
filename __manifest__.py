# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Cotizador: importar desde planillas de Odoo",
    "summary": "Importa la planilla de configuraciones desde una planilla de Odoo (spreadsheet_oca)",
    # Sin esto Odoo muestra README.md interpretándolo como reStructuredText
    "description": "Importa la matriz del cotizador desde una planilla de Odoo. Documentación: README.md.",
    "version": "19.0.1.0.0",
    "author": "Franco Funes",
    "license": "AGPL-3",
    "depends": ["cotizador", "spreadsheet_oca"],
    "data": [
        "views/import_wizard_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "cotizador_spreadsheet/static/src/analyze_action_loader.js",
        ],
        "spreadsheet.o_spreadsheet": [
            "cotizador_spreadsheet/static/src/analyze_action.js",
        ],
    },
    "auto_install": True,
    "installable": True,
}
