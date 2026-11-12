# Cotizador: importar desde planillas de Odoo

Puente entre el [cotizador](https://github.com/ffunes-cru/cotizador) y `spreadsheet_oca`
([OCA/spreadsheet](https://github.com/OCA/spreadsheet)). Se instala solo cuando están los dos.

Agrega al importador de la matriz (*Ventas › Configuración › Configurador Sembradoras › Importar
Configuraciones*) el origen **Planilla de Odoo**: en lugar de subir un CSV o un Excel, se elige una
planilla de Odoo. La planilla de configuraciones se trabaja en Odoo, con fórmulas, y se importa sin exportar nada.

La planilla puede tener el formato del CSV del importador o el de la **planilla de configuraciones**. Los dos
formatos, la conversión y los cuidados están en la documentación del cotizador:
`docs/importador.md` §11.

## Cómo funciona

Las fórmulas de una planilla de Odoo se calculan en el navegador: el servidor solo guarda el texto de
cada fórmula. Por eso, al **Analizar**:

1. al elegir la planilla se listan sus hojas; se marcan las de las máquinas a importar;
2. `action_analyze()` devuelve la acción cliente `cotizador_spreadsheet_analyze`
   (`static/src/analyze_action.js`, que se carga con el bundle de o-spreadsheet);
3. la acción carga la planilla con los cambios sin guardar, la calcula y lee las hojas marcadas: valores,
   texto visible (números con coma decimal), columnas ocultas y celdas combinadas;
4. manda las hojas a `action_analyze_spreadsheet()`. El cotizador las convierte y las analiza igual que
   un archivo (`models/config_sheet.py`).

## Tests

```bash
./odoo-bin -d <base> -i cotizador_spreadsheet --test-tags /cotizador_spreadsheet --stop-after-init
```

El test arma una planilla con fórmulas, una columna oculta y celdas combinadas, la analiza desde el
navegador (Chrome headless) y la importa.

## Licencia y créditos

AGPL-3.0 o posterior (ver `LICENSE`), como el cotizador y `spreadsheet_oca`, del que depende.

- Editor de planillas: [`spreadsheet_oca`](https://github.com/OCA/spreadsheet/tree/19.0/spreadsheet_oca), de
  CreuBlanca y la Odoo Community Association (OCA), AGPL-3.
- Motor de planillas: [o-spreadsheet](https://github.com/odoo/o-spreadsheet), de Odoo S.A., incluido en el módulo
  `spreadsheet` de Odoo Community (LGPL-3).

Este módulo no copia código de esos proyectos: los usa como dependencias.
