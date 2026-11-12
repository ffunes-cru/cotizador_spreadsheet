"""@file
Origen "Planilla de Odoo" del importador del cotizador.

Las fórmulas de una planilla de Odoo se calculan en el navegador (o-spreadsheet), no en el servidor:
el JSON guardado tiene el texto de la fórmula, no su resultado. Por eso el análisis va y vuelve:

1. action_analyze() devuelve la acción cliente `cotizador_spreadsheet_analyze`
   (static/src/analyze_action.js), que carga la planilla con sus cambios sin guardar, la calcula y
   lee cada hoja (valores, texto visible, columnas ocultas y celdas combinadas);
2. esa acción llama a action_analyze_spreadsheet() con las hojas, que sigue como con un archivo:
   cotizador convierte la planilla de configuraciones al formato del CSV y la analiza.
"""
from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.cotizador.models.config_sheet import workbook_sheet_names


class SembradoraImportWizard(models.TransientModel):
    """Agrega al importador el origen *Planilla de Odoo*."""
    _inherit = 'sembradora.import.wizard'

    source = fields.Selection(
        [('files', 'Archivos CSV o Excel'), ('spreadsheet', 'Planilla de Odoo')],
        string='Origen', default='files', required=True,
    )
    spreadsheet_id = fields.Many2one(
        'spreadsheet.spreadsheet', string='Planilla',
        help='Planilla con la matriz, en el formato del importador o en el de la planilla de configuraciones. '
             'Se leen todas las hojas visibles que tienen alguno de los dos encabezados.',
    )

    @api.onchange('source', 'spreadsheet_id', 'csv_file_ids')
    def _onchange_csv_file_ids(self):
        """Lista las hojas de la planilla de Odoo elegida, o las de los .xlsx adjuntos."""
        if self.source != 'spreadsheet':
            return super()._onchange_csv_file_ids()
        sheet = self.spreadsheet_id
        self._set_sheets([(sheet.name, self._spreadsheet_sheet_names(sheet))] if sheet else [])
        return None

    def _spreadsheet_sheet_names(self, sheet):
        """Hojas visibles de una planilla de Odoo, de su última versión guardada.

        Una planilla subida como .xlsx y todavía no guardada desde Odoo tiene el libro tal cual.

        @param sheet spreadsheet.spreadsheet.
        @return Lista de nombres.
        """
        raw = sheet.spreadsheet_raw or {}
        if 'sheets' in raw:
            return [s['name'] for s in raw['sheets'] if s.get('isVisible', True)]
        if 'xl/workbook.xml' in raw:
            return workbook_sheet_names(raw['xl/workbook.xml'])
        return []

    def action_analyze(self):
        """Con una planilla de Odoo, la calcula en el navegador antes de analizarla.

        @return Acción cliente que lee la planilla, o la del análisis de archivos.
        @throws UserError Si no se eligió la planilla.
        """
        self.ensure_one()
        if self.source != 'spreadsheet':
            return super().action_analyze()
        if not self.spreadsheet_id:
            raise UserError("Elija la planilla a importar.")
        self.spreadsheet_id.check_access('read')
        return {
            'type': 'ir.actions.client',
            'tag': 'cotizador_spreadsheet_analyze',
            'params': {'wizard_id': self.id, 'spreadsheet_id': self.spreadsheet_id.id,
                       'sheet_names': self._selected_sheets(self.spreadsheet_id.name)},
        }

    def action_analyze_spreadsheet(self, grids):
        """Analiza las hojas de la planilla ya calculadas en el navegador.

        @param grids Hojas marcadas (dicts de grilla de cotizador/models/config_sheet.py).
        @return Acción que reabre el asistente con el análisis.
        @throws UserError Si el asistente no está esperando una planilla o ninguna hoja se puede leer.
        """
        self.ensure_one()
        if self.state != 'draft' or self.source != 'spreadsheet' or not self.spreadsheet_id:
            raise UserError("El asistente no está esperando una planilla para analizar.")
        if not isinstance(grids, list) or not all(isinstance(g, dict) for g in grids):
            raise UserError("Las hojas de la planilla no llegaron en el formato esperado.")
        notes = []
        files = self._files_from_grids(self.spreadsheet_id.name, grids, notes)
        action = self._analyze(files, from_sheets=True, notes=notes)
        # Llega por orm.call, no por un botón: el cliente no completa `views` a partir de `view_mode`
        return {**action, 'views': [(False, 'form')]}
