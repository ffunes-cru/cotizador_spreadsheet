"""@file
Importar la planilla de configuraciones desde una planilla de Odoo, con las fórmulas calculadas en el navegador."""
import json

from odoo import Command
from odoo.tests import Form, HttpCase, tagged

from odoo.addons.cotizador.tests.common import find_config
from odoo.addons.cotizador.tests.test_config_sheet import CONFIG_SHEET_VALUES

## Arma la planilla con comandos de o-spreadsheet (precio de la máquina como fórmula sobre la columna
## oculta de costo, regla en celdas combinadas, hoja auxiliar) y la guarda.
BUILD_JS = """
(async () => {
    const env = odoo.__WOWL_DEBUG__.root.env;
    const orm = env.services.orm;
    await odoo.loader.modules.get("@web/core/assets").loadBundle("spreadsheet.o_spreadsheet");
    const { Model } = odoo.loader.modules.get("@odoo/o-spreadsheet");
    const model = new Model();
    const sheetId = model.getters.getActiveSheetId();
    model.dispatch("RENAME_SHEET", { sheetId, oldName: model.getters.getSheetName(sheetId), newName: "Pionera" });
    %(values)s.forEach((cells, row) => cells.forEach((value, col) => {
        if (value !== "") {
            model.dispatch("UPDATE_CELL", { sheetId, col, row, content: String(value) });
        }
    }));
    model.dispatch("UPDATE_CELL", { sheetId, col: 4, row: 4, content: "=D5+1" });
    // Distancia como número (52.5): se lee con coma decimal, sin importar el idioma de la planilla
    model.dispatch("UPDATE_CELL", { sheetId, col: 2, row: 4, content: "52.5" });
    model.dispatch("ADD_MERGE", { sheetId, target: [{ left: 7, right: 8, top: 2, bottom: 2 }], force: true });
    model.dispatch("HIDE_COLUMNS_ROWS", { sheetId, dimension: "COL", elements: [3] });
    // Fila de datos oculta (Tolva Grande, fila 6): no se lee y se avisa
    model.dispatch("HIDE_COLUMNS_ROWS", { sheetId, dimension: "ROW", elements: [5] });
    model.dispatch("CREATE_SHEET", { sheetId: "costos", position: 1, name: "Costos" });
    model.dispatch("UPDATE_CELL", { sheetId: "costos", col: 0, row: 0, content: "Chasis" });
    await orm.write("spreadsheet.spreadsheet", [%(spreadsheet_id)d], { spreadsheet_raw: model.exportData() });
    console.log("test successful");
})().catch((e) => console.error("test failed: " + e + " " + (e.cause || "") + "\\n" + e.stack));
"""

## Analiza con el asistente (botón Analizar): la acción calcula la planilla en el navegador.
ANALYZE_JS = """
(async () => {
    const env = odoo.__WOWL_DEBUG__.root.env;
    const orm = env.services.orm;
    const action = await orm.call("sembradora.import.wizard", "action_analyze", [[%(wizard_id)d]]);
    await env.services.action.doAction(action);
    for (let i = 0; i < 100 && !document.querySelector(".modal .o_form_view"); i++) {
        await new Promise((resolve) => setTimeout(resolve, 100));
    }
    console.log("test successful");
})().catch((e) => console.error("test failed: " + e + " " + (e.cause || "") + "\\n" + e.stack));
"""


@tagged('post_install', '-at_install')
class TestSpreadsheetImport(HttpCase):
    """El origen *Planilla de Odoo* del importador."""

    def test_import_from_odoo_spreadsheet(self):
        """La planilla se calcula en el navegador y se analiza e importa como la planilla de configuraciones."""
        self.env.ref('base.user_admin').write({'group_ids': [Command.link(self.env.ref('cotizador.group_cotizador_manager').id)]})
        if 'tour_enabled' in self.env['res.users']._fields:
            self.env.ref('base.user_admin').tour_enabled = False
        sheet = self.env['spreadsheet.spreadsheet'].create({'name': 'Matriz Pionera'})
        wizard = self.env['sembradora.import.wizard'].create({
            'source': 'spreadsheet', 'spreadsheet_id': sheet.id, 'currency_id': self.env.ref('base.USD').id,
        })
        ready = '!!(odoo.__WOWL_DEBUG__ && odoo.__WOWL_DEBUG__.root)'
        self.browser_js('/odoo?debug=1', BUILD_JS % {'values': json.dumps(CONFIG_SHEET_VALUES), 'spreadsheet_id': sheet.id},
                        ready=ready, login='admin', timeout=120)

        # Al elegir la planilla, el asistente lista sus hojas; se marca la de la máquina
        wizard._onchange_csv_file_ids()
        self.assertEqual(wizard.sheet_ids.mapped('name'), ['Pionera', 'Costos'])
        wizard.sheet_ids.filtered(lambda s: s.name == 'Pionera').selected = True
        self.browser_js('/odoo?debug=1', ANALYZE_JS % {'wizard_id': wizard.id}, ready=ready, login='admin', timeout=120)

        wizard.invalidate_recordset()
        self.assertEqual(wizard.state, 'analyzed')
        self.assertFalse(wizard.has_errors, wizard.analysis_summary)
        self.assertIn('Configuraciones nuevas: <b>2</b>', wizard.analysis_summary)
        self.assertTrue(wizard.normalized_csv)
        self.assertIn('no se leyeron 1 filas de datos ocultas (6)', wizard.analysis_summary)
        wizard.action_import()
        config = find_config(self.env, 'Pionera', '16 Lineas', '52,5')
        self.assertEqual(config.price, 1000.0)  # =D5+1, con D oculta (no es atributo)
        self.assertEqual(sorted(config.value_ids.mapped('name')), ['16 Lineas', '52,5'])
        lines = {line.product_id.name: line for line in config.accessory_line_ids}
        self.assertEqual(lines['Kit Grueso'].rule_ids.rule_type, 'choice')  # regla en celdas combinadas
        self.assertNotIn('Tolva - Grande', lines)  # su fila está oculta

    def test_sheet_list_in_form(self):
        """Desde el formulario (como el navegador): elegir la planilla lista sus hojas; marcar una y guardar."""
        sheet = self.env['spreadsheet.spreadsheet'].create({
            'name': 'Libro', 'spreadsheet_raw': {'sheets': [{'id': 'a', 'name': 'Gringa'}, {'id': 'b', 'name': 'Costos'},
                                                            {'id': 'c', 'name': 'Oculta', 'isVisible': False}]},
        })
        form = Form(self.env['sembradora.import.wizard'])
        form.currency_id = self.env.ref('base.USD')
        form.source = 'spreadsheet'
        form.spreadsheet_id = sheet
        self.assertEqual(len(form.sheet_ids), 2)
        with form.sheet_ids.edit(0) as line:
            line.selected = True
        wizard = form.save()
        self.assertEqual(wizard.sheet_ids.mapped('name'), ['Gringa', 'Costos'])
        action = wizard.action_analyze()
        self.assertEqual(action['params']['sheet_names'], ['Gringa'])

    def test_sheet_required(self):
        """Sin hojas marcadas, el análisis pide marcarlas antes de ir al navegador."""
        sheet = self.env['spreadsheet.spreadsheet'].create({'name': 'Vacía'})
        wizard = self.env['sembradora.import.wizard'].create({
            'source': 'spreadsheet', 'spreadsheet_id': sheet.id, 'currency_id': self.env.ref('base.USD').id,
        })
        with self.assertRaisesRegex(Exception, 'marque las hojas a importar'):
            wizard.action_analyze()

    def test_files_source_unchanged(self):
        """Con el origen de archivos, el asistente analiza los adjuntos como siempre."""
        wizard = self.env['sembradora.import.wizard'].create({'currency_id': self.env.ref('base.USD').id})
        self.assertEqual(wizard.source, 'files')
        with self.assertRaisesRegex(Exception, 'Seleccione al menos un archivo'):
            wizard.action_analyze()
