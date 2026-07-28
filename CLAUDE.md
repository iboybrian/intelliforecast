# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Demo de forecast de demanda mensual + KPIs de inventario. Dos piezas:

- **`pipeline.py`** — batch. Lee CSVs, agrega a mensual, clasifica demanda, corre backtesting con modelos de `statsforecast`, escribe parquets.
- **`app.py`** — dashboard Streamlit (3 pestañas: Vista general, Riesgo de quiebre, Sobre-stock). Lee los parquets y puede disparar `pipeline.py` desde la UI (ver "Carga de datos" abajo); no calcula forecast por sí mismo.
- **`gen_reporte.py`** — aparte del flujo anterior. No lee parquets: arma un HTML autocontenido con los PNG de `assets/` en base64 y lo imprime a PDF con Chrome/Edge headless (`--print-to-pdf`). Rutas de Chrome hardcodeadas para Windows (`CHROME_CANDIDATES`). Los screenshots de `assets/` se actualizan a mano. **No es genérico**: es un entregable comercial de 3 páginas para un cliente concreto — logo, textos, paleta y la URL pública del demo están hardcodeados en `build_html()`. Salidas: `reporte_premiumpet.html` + `reporte_premiumpet.pdf`.

## Commands

```bash
# 1. Instalar deps
pip install -r requirements.txt

# 2. Generar resultados.parquet + historico.parquet (correr ANTES del dashboard)
python pipeline.py
python pipeline.py --check   # self-check del ETL (mapeo, formato de fecha, agregación, MASE)

# 3. Dashboard (lee los parquets del paso 2)
streamlit run app.py
# o, si "streamlit" no está en PATH:
python -m streamlit run app.py

# Opcional — reporte PDF comercial desde los PNG de assets/ (no toca los parquets).
python gen_reporte.py
```

`rebalance_inventario.py` está **obsoleto — no correrlo tal cual**. Lee `inventario_original.csv`, que es el dataset viejo del demo (60 SKUs `SKU_001…`, headers canónicos `sku,existencia,pack,lead_time_dias`). Contra los datos actuales el join da **0 filas de overlap**, y además escribiría `inventario.csv` con headers canónicos, rompiendo el mapeo de `carga.json`. Sirve solo como referencia de cómo calibrar existencias a un DOH objetivo a partir de `resultados.parquet`; para reusarlo hay que reapuntarlo al inventario vigente y preservar sus headers.

Sin linter ni build; el único test es `pipeline.py --check`. Corrida completa = pipeline.py una vez, luego streamlit. Después de re-correr pipeline.py con la app abierta, hay que limpiar la cache de Streamlit (`st.cache_data.clear()` vía el menú, o reiniciar el proceso) — la app no detecta cambios en el parquet solo por mtime.

Deps no obvias en `requirements.txt`: `pyarrow` (escribir parquet), `XlsxWriter` (export de la app), `Pillow` (logo del sidebar), `utilsforecast` (MASE). Al tocar imports, actualizar el archivo — el deploy en Streamlit Cloud instala solo desde ahí.

## Flujo de datos (el "big picture")

```
ventas_historicas.csv  ┐
inventario.csv         ┤→ pipeline.py → resultados.parquet ┐
carga.json (opcional)  ┘                historico.parquet  ┘→ app.py (Streamlit)
```

- **`ventas_historicas.csv`**: los headers son libres — `carga.json` dice cuál es cuál. Campos requeridos: `sku, centro_distribucion, fecha, cantidad`. `pipeline.py` crea `unique_id = sku|centro_distribucion` — esa es la llave de serie en todo el sistema — y agrega a mensual con `aggregate_monthly()` antes de cualquier otro cálculo.
- **`inventario.csv`**: requeridos `sku, existencia`. `centro_distribucion`, `pack` y `lead_time_dias` son **opcionales**: si faltan (o si el SKU no está en el archivo) los dos últimos se rellenan con `INV_DEFAULTS` = 1 y 30 días, pisables desde la UI vía `carga.json["defaults"]`. Ojo: un lead time inventado produce un `estado_inventario` inventado.

  **`centro_distribucion` decide el modo de cálculo** (`resolver_existencia_por_cd`): mapeado → **join directo** `sku+CD` contra las ventas, cada tienda se queda con su propia existencia (varias filas por sku-CD se **suman**, para que el join no haga fan-out y duplique la combinación en el parquet). Sin mapear → se **prorratea** la existencia del SKU entre sus CDs proporcional al histórico. Los dos caminos son join LEFT sobre las ventas: una combinación con ventas y sin fila de inventario entra con existencia 0 → Riesgo de quiebre, y se imprime el conteo. Las llaves se castean a String de los dos lados: un `tienda_id` numérico no cruzaría contra el `centro_distribucion` string de las series. Si el overlap da **0**, se imprime un AVISO con ejemplos de centros de cada lado — es el modo de falla silencioso típico (id vs nombre de tienda, ceros a la izquierda).

  **Trampa de escala** (costó una sesión entera de debug): `existencia` tiene que estar en las **mismas unidades** que `cantidad` de ventas. Si el archivo de inventario viene en otra escala (cajas vs unidades, snapshot de una sola tienda, muestra parcial), todos los KPIs salen basura pero *sin error* — DOH de horas, el 100% de los SKUs en Riesgo de quiebre. Peor: **en el camino de prorrateo** esa existencia se divide entre los CDs del SKU, así que un número ya pequeño se vuelve fracción (`0.03`) y la UI lo muestra como **`0`** por el `.round(0)` de las tablas. Antes de culpar al código, comparar existencia total contra ventas mensuales totales: si el stock no cubre ni unos pocos días de demanda, el problema son los datos.
- **`carga.json`** (opcional, escrito por app.py en cada "Procesar"): mapeo de columnas y dimensiones extra. `columnas` es **destino → origen** (`{"sku": "SKU_Coded", …}`), `formato_fecha` es un strftime (`"%d/%m/%Y"`) o `"auto"`, `dimensiones` es una lista de headers de origen que se propagan tal cual a los parquets. Ausente → mapeo identidad sobre los nombres canónicos, fecha auto y **auto-descubrimiento** de dimensiones (toda columna sobrante); por eso `python pipeline.py` a secas sigue funcionando y sigue propagando `proveedor`/`categoria`. Reemplaza al viejo `dimensiones.json`, que ya no se lee.
- **`resultados.parquet`**: una fila por combinación SKU-CD con clasificación, modelo ganador, MASE, forecast de 4 meses, `n_periodos`/`flag_serie_corta` y todos los KPIs.
- **`historico.parquet`**: serie mensual larga (post-agregación) para graficar en los drill-downs; incluye las dimensiones extra.

La escritura CSV → `carga.json` → subproceso **no es atómica**: un crash entre pasos deja el mapeo desincronizado de los datos. Se vuelve a alinear con el siguiente "Procesar".

## Lógica clave de pipeline.py

0. **Lectura lazy** (`scan_lado` + `aggregate_monthly`): `pl.scan_csv` + `select(pl.col(origen).alias(destino))` — el `select` (no `rename`) es lo que habilita projection pushdown, así un CSV de 1.5M filas solo se parsea en las columnas mapeadas. El **único `.collect()`** del lado ventas está al final de `aggregate_monthly`; de ahí en adelante todo es eager sobre `n_series × n_meses`. Las filas con fecha ilegible caen en un bucket `null` y se cuentan en la misma pasada en vez de reventar.
1. **Agregación mensual** (`aggregate_monthly`): suma `cantidad` por mes calendario (`dt.truncate("1mo")`) antes de clasificar/pronosticar. Todo lo que sigue trabaja en base mensual. Las dimensiones extra viajan como `.first()` dentro del `agg`, **nunca** como llave del `group_by`: en la llave partirían la serie en varias filas por mes y el forecast saldría basura sin avisar.
2. **Clasificación SBC** (`classify_demand`): ADI y CV² por serie → cuadrantes Smooth / Erratic / Intermittent / Lumpy con umbrales `ADI_THRESHOLD=1.32`, `CV2_THRESHOLD=0.49`. **Estos umbrales están duplicados en `app.py`** (para dibujar los cuadrantes del scatter) — si cambian, cambiar en ambos.
3. **Dos familias de modelos** (`FAMILIES` dict): Smooth/Erratic → modelos regulares (AutoETS, AutoARIMA, Theta, SeasonalNaive). Intermittent/Lumpy → modelos intermitentes (CrostonClassic, TSB, ADIDA). `build_forecast_table` itera `FAMILIES` y corre cada grupo aparte; los nombres de modelo se derivan con `str(m)` (mismo alias que usa statsforecast para nombrar columnas).
4. **Selección de modelo** (`backtest_and_forecast`): cross-validation temporal (rolling origin, `N_WINDOWS=3`, `STEP_SIZE=4`), gana el menor **MASE no estacional** (`seasonality=1`, deliberado por series cortas/intermitentes). El MASE pasa siempre por `_mase_valido()` antes del `sort`: polars ordena los `null` **primero**, así que sin eso un MASE nulo gana la selección. El refit final es solo del modelo ganador (un `sf.forecast` por modelo sobre su subconjunto), no de los 4.
4b. **Series cortas** (`forecast_corto`): con menos de `MIN_PERIODOS` (=16, derivado de `H`/`STEP_SIZE`/`N_WINDOWS`/`MIN_TRAIN`) el rolling origin no da — statsforecast levanta `ValueError` antes de instanciar el modelo, y `fallback_model` no lo cubre. Esas series van por una rama de polars puro: SeasonalNaive degenerado (último valor), MASE de holdout de 1 punto y `flag_serie_corta = True`. Ese MASE **no es comparable** con el de las series largas — el drill-down lo advierte.
5. **KPIs** (`calcular_kpis`): `resolver_existencia_por_cd` deja la existencia al grano SKU-CD — join directo si el inventario trae `centro_distribucion`, prorrateo proporcional al histórico si no (ver la sección de `inventario.csv` arriba); la columna resultante es `existencia_cd` en ambos casos. Deriva DOH/WOS/MOH (demanda diaria = `forecast_mensual_promedio / 30.44`), `estado_inventario` (Riesgo de quiebre si DOH < lead_time_dias / Sobre-stock si DOH > 120d / Normal en medio) y `cantidad_reorden` — cubre `LEAD_TIME_BUFFER=1.5` veces el lead time, redondeada al múltiplo de `pack`.

`StatsForecast` se construye con `n_jobs=-1` (≈3x, mismos números) y `fallback_model=SeasonalNaive(season_length=1)` para que una serie que reviente no tumbe la corrida. **No hay muestreo ni tiers de modelos rápidos**: la precisión manda, así que una carga grande tarda lo que tarda (~0.3 s/serie de familia regular; 30k series ≈ 2 h) — por eso el preflight de la UI.

`H=4` (horizonte en meses), `SEASON_LENGTH=12`, `FREQ="1mo"` (offset **polars**, no pandas — `statsforecast` valida freq contra polars cuando el df es polars; usar `"MS"` u otro alias pandas revienta con `ValueError`) son constantes de pipeline.py.

## Convenciones de app.py

- **Todo en polars** (no pandas), incluso alimentando plotly con `.to_list()`.
- **i18n**: dict `STRINGS["es"|"en"]`; toda cadena visible sale de `TXT[...]`. Al añadir texto, agregar la llave en **ambos** idiomas.
- **Datos canónicos en español**: `estado_inventario`/`clasificacion` se guardan en español en el parquet; se traducen a la vista con `ESTADO_MAP`/`CLASE_MAP` según idioma. Los filtros comparan contra los valores mapeados (`estado_riesgo`, etc.), no contra literales.
- **`@st.cache_data` en `load()`**: no invalida por cambios en disco — ver nota de Commands arriba.
- **Filtros** (barra superior, no sidebar): Centro, Tipo de SKU (multiselect), Proveedor, Categoría. Los dos últimos usan `filtro_opcional()` — si la columna no existe en `resultados.parquet` el selector aparece deshabilitado en vez de desaparecer. Si `carga.json` aporta dimensiones presentes en `resultados.parquet`, aparece además un multiselect "➕ Agregar filtros" (vacío por defecto) para sumar selectboxes dinámicos sobre esas dimensiones, reusando `filtro_opcional()`. Todo lo que se muestra en las 3 pestañas parte de `res_f` (resultado ya filtrado).
- **Carga de datos** (sidebar, expander "Cargar tus datos"): dos `file_uploader` + un selectbox de mapeo **por cada campo** (`_mapeo`, preseleccionado al header homónimo si existe), selectbox de formato de fecha, selectboxes opcionales de `pack`/`lead_time_dias` con su `number_input` de respaldo, y multiselects de dimensiones. Todos los widgets llevan `key` por identidad de archivo (`nombre_tamaño`) para no crashear al cambiar de archivo. La validación (campos sin asignar, misma columna en dos campos) es **puro estado de UI: no se lee ni una fila de datos**, y bloquea el botón antes de tocar el disco. `escribir_carga()` copia los bytes crudos con `shutil.copyfileobj` (nunca `read_csv` en el proceso de Streamlit: duplicaría 1.5M filas en RAM) y escribe `carga.json`. Después `contar_series()` hace el preflight con `scan_csv`; sobre `UMBRAL_SERIES` (2000) pide confirmación explícita y sugiere correr `python pipeline.py` en terminal. `correr_pipeline()` lanza el subproceso con `Popen(..., "-u", stderr=STDOUT)` y transmite la salida línea a línea en un `st.status`; si falla no limpia la cache (los parquets viejos siguen sirviendo). No hace backup de los CSVs originales antes de sobrescribir.
- **Export**: `exportar_excel()` arma el xlsx en memoria con `xlsxwriter` (hoja KPIs = tabla visible, hoja Historico 24m = últimos 24 meses de las series filtradas). Se dispara desde `boton_descarga()` en cada pestaña. El `Workbook` va con `nan_inf_to_errors: True` — sin eso, un solo MASE `inf` (serie de train constante, ver `_mase_valido()`) revienta la descarga entera con `TypeError: NAN/INF not supported in write_number()`.
- Paleta y layout de plotly centralizados arriba (`BG_*`, `ACCENT_*`, `PLOTLY_LAYOUT`, helper `axis()`). CSS inyectado en `inject_css()` fuerza texto blanco, oculta la barra superior de Streamlit (sin ocultar el botón de colapsar sidebar — usar `background: transparent`, no `display: none`, si se retoca) y estiliza el `file_uploader`.

## Notas

- `.streamlit_run.sh` tiene una ruta absoluta hardcodeada de otra máquina — no usar tal cual.
- **Estado de los CSVs del demo** (sintéticos, editados a mano): `ventas_historicas.csv` fue consolidado a un solo centro (`Store_Number = 1`, antes 35) y las existencias de `inventario.csv` escaladas para que la distribución de estados quede repartida. Por eso el filtro de Centro tiene un único valor y hay ~659 series en vez de ~18k. Los originales están en `*_bak.csv`.
