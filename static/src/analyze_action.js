/**
 * @file
 * Acción `cotizador_spreadsheet_analyze`: calcula la planilla elegida en el importador y le manda
 * las hojas al servidor (sembradora.import.wizard.action_analyze_spreadsheet).
 *
 * Las fórmulas se calculan acá porque el servidor solo tiene el texto de cada fórmula. Se incluyen
 * los cambios todavía sin guardar (revisiones) de quien esté editando la planilla.
 */

import { registry } from "@web/core/registry";
import * as spreadsheet from "@odoo/o-spreadsheet";

const { Model, load } = spreadsheet;

/**
 * Hojas de un modelo de o-spreadsheet ya calculado, en el formato de grilla del importador
 * (cotizador/models/config_sheet.py): valores, texto visible, columnas y filas ocultas (a mano o
 * por un filtro), celdas combinadas y si la hoja está oculta. Se recortan las filas y columnas vacías
 * del final.
 *
 * Antes de leer, el modelo pasa a formatear los números con **coma decimal**: el texto visible de un
 * atributo (`17,5`) no puede depender del idioma de la planilla (un .xlsx importado queda en inglés,
 * `17.5`), porque es parte de la identidad del valor. Es lo que hacía Google Sheets y lo que hace la
 * lectura de .xlsx (`config_sheet.cell_text()`). El cambio es solo en este modelo, no se guarda.
 *
 * @param {Model} model Modelo de o-spreadsheet (se le cambia el formato de números).
 * @param {string[]} [sheetNames] Hojas a leer; todas si no se indica.
 * @returns {Object[]} Una grilla por hoja leída.
 */
export function readGrids(model, sheetNames) {
    const getters = model.getters;
    const locale = {
        ...getters.getLocale(),
        decimalSeparator: ",",
        thousandsSeparator: ".",
        formulaArgSeparator: ";",
    };
    const result = model.dispatch("UPDATE_LOCALE", { locale });
    if (!result.isSuccessful) {
        throw new Error(`No se pudo leer la planilla con coma decimal (${result.reasons})`);
    }
    const sheetIds = getters
        .getSheetIds()
        .filter((sheetId) => !sheetNames || sheetNames.includes(getters.getSheetName(sheetId)));
    return sheetIds.map((sheetId) => {
        const numberRows = getters.getNumberRows(sheetId);
        const numberCols = getters.getNumberCols(sheetId);
        const values = [];
        const display = [];
        let lastRow = -1;
        let lastCol = -1;
        for (let row = 0; row < numberRows; row++) {
            const rowValues = [];
            const rowDisplay = [];
            for (let col = 0; col < numberCols; col++) {
                const cell = getters.getEvaluatedCell({ sheetId, col, row });
                const value = cell.value === undefined || cell.value === "" ? null : cell.value;
                const text = cell.formattedValue || "";
                rowValues.push(value);
                rowDisplay.push(text);
                if (value !== null || text) {
                    lastRow = row;
                    lastCol = Math.max(lastCol, col);
                }
            }
            values.push(rowValues);
            display.push(rowDisplay);
        }
        const trim = (rows) => rows.slice(0, lastRow + 1).map((row) => row.slice(0, lastCol + 1));
        const hiddenCols = [];
        for (let col = 0; col <= lastCol; col++) {
            if (getters.isColHiddenByUser(sheetId, col)) {
                hiddenCols.push(col);
            }
        }
        const hiddenRows = [];
        for (let row = 0; row <= lastRow; row++) {
            if (getters.isRowHidden(sheetId, row)) {
                hiddenRows.push(row);
            }
        }
        return {
            name: getters.getSheetName(sheetId),
            values: trim(values),
            display: trim(display),
            hidden_cols: hiddenCols,
            hidden_rows: hiddenRows,
            merges: getters.getMerges(sheetId).map((m) => [m.top, m.left, m.bottom, m.right]),
            hidden: !getters.isSheetVisible(sheetId),
        };
    });
}

/**
 * Lee la planilla (con sus revisiones sin guardar), la calcula y manda a analizar las hojas marcadas.
 *
 * @param {Object} env Entorno del cliente web.
 * @param {Object} action Acción con `params.wizard_id`, `params.spreadsheet_id` y `params.sheet_names`.
 * @returns {Promise<Object>} Acción que reabre el asistente con el análisis.
 */
async function analyzeSpreadsheet(env, action) {
    const { wizard_id: wizardId, spreadsheet_id: spreadsheetId, sheet_names: sheetNames } = action.params;
    const orm = env.services.orm;
    const data = await orm.call("spreadsheet.spreadsheet", "get_spreadsheet_data", [[spreadsheetId]]);
    const model = new Model(load(data.spreadsheet_raw), {}, data.revisions);
    const grids = readGrids(model, sheetNames);
    return orm.call("sembradora.import.wizard", "action_analyze_spreadsheet", [[wizardId], grids]);
}

registry.category("actions").add("cotizador_spreadsheet_analyze", analyzeSpreadsheet, { force: true });
