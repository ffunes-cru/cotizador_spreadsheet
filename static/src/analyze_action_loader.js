/**
 * @file
 * Carga diferida de la acción `cotizador_spreadsheet_analyze` (analyze_action.js).
 *
 * La acción usa o-spreadsheet, que está en el bundle `spreadsheet.o_spreadsheet` y no en el backend:
 * esta función carga el bundle, que reemplaza la acción en el registro, y la vuelve a ejecutar
 * (mismo mecanismo que las acciones de spreadsheet del core).
 */

import { addSpreadsheetActionLazyLoader } from "@spreadsheet/assets_backend/spreadsheet_action_loader";

addSpreadsheetActionLazyLoader("cotizador_spreadsheet_analyze");
