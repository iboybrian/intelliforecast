# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Demo de forecast de demanda mensual + KPIs de inventario. Dos piezas:

- **`pipeline.py`** — batch. Lee CSVs, agrega a mensual, clasifica demanda, corre backtesting con modelos de `statsforecast`, escribe parquets.
- **`app.py`** — dashboard Streamlit (3 pestañas: Vista general, Riesgo de quiebre, Sobre-stock). Lee los parquets y puede disparar `pipeline.py` desde la UI (ver "Carga de datos" abajo); no calcula forecast por sí mismo.

## Commands

```bash
# 1. Instalar deps (requirements.txt está INCOMPLETO — ver nota abajo)
pip install polars plotly streamlit statsforecast utilsforecast pyarrow

# 2. Generar resultados.parquet + historico.parquet (correr ANTES del dashboard)
python pipeline.py

# 3. Dashboard (lee los parquets del paso 2)
streamlit run app.py
# o, si "streamlit" no está en PATH:
python -m streamlit run app.py

# Opcional — rebalancear existencias del demo para distribución de estados más variada.
# Requiere resultados.parquet ya generado; reescribe inventario.csv desde inventario_original.csv.
python rebalance_inventario.py   # luego re-correr pipeline.py
```

Sin tests, linter, ni build. Corrida completa = pipeline.py una vez, luego streamlit. Después de re-correr pipeline.py con la app abierta, hay que limpiar la cache de Streamlit (`st.cache_data.clear()` vía el menú, o reiniciar el proceso) — la app no detecta cambios en el parquet solo por mtime.

**`requirements.txt` está incompleto**: lista `polars/plotly/streamlit` pero pipeline.py importa `statsforecast` y `utilsforecast` (y `pyarrow` para escribir parquet). Al tocar deps, actualizar el archivo.

## Flujo de datos (el "big picture")

```
ventas_historicas.csv  ┐
inventario.csv         ┘→ pipeline.py → resultados.parquet ┐
                                        historico.parquet  ┘→ app.py (Streamlit)
```

- **`ventas_historicas.csv`**: `sku, fecha, cantidad, centro_distribucion`, semanal en el CSV crudo. `pipeline.py` crea `unique_id = sku|centro_distribucion` — esa es la llave de serie en todo el sistema — y luego agrega a mensual con `aggregate_monthly()` antes de cualquier otro cálculo.
- **`inventario.csv`**: `sku, existencia, pack, lead_time_dias` (existencia a nivel SKU, no por CD). Columnas opcionales `proveedor`/`categoria` (ver `OPTIONAL_SKU_COLS`) se propagan a `resultados.parquet` si están presentes; si no, se ignoran sin error — existen solo para alimentar los filtros opcionales del dashboard. `OPTIONAL_SKU_COLS` es un mecanismo **aparte** de `dimensiones.json` (abajo).
- **`resultados.parquet`**: una fila por combinación SKU-CD con clasificación, modelo ganador, MASE, forecast de 4 meses y todos los KPIs.
- **`historico.parquet`**: serie mensual larga (post-agregación) para graficar en los drill-downs.
- **`dimensiones.json`** (opcional, escrito por app.py en cada "Procesar", incluso vacío): columnas extra elegidas por el usuario al subir los CSVs — `{columna, origen, label}`, donde `label` es el **nombre de la columna** (header). `pipeline.py` (`load_dim_config`/`propagate_extra_dims`) las une a `resultados.parquet` por `sku` (origen inventario) o `sku+centro_distribucion` (origen ventas), sin pisar columnas existentes. Ausente → sin efecto (compat con `python pipeline.py` a secas).

## Lógica clave de pipeline.py

1. **Agregación mensual** (`aggregate_monthly`): suma `cantidad` semanal por mes calendario (`dt.truncate("1mo")`) antes de clasificar/pronosticar. Todo lo que sigue trabaja en base mensual.
2. **Clasificación SBC** (`classify_demand`): ADI y CV² por serie → cuadrantes Smooth / Erratic / Intermittent / Lumpy con umbrales `ADI_THRESHOLD=1.32`, `CV2_THRESHOLD=0.49`. **Estos umbrales están duplicados en `app.py`** (para dibujar los cuadrantes del scatter) — si cambian, cambiar en ambos.
3. **Dos familias de modelos** (`FAMILIES` dict): Smooth/Erratic → modelos regulares (AutoETS, AutoARIMA, Theta, SeasonalNaive). Intermittent/Lumpy → modelos intermitentes (CrostonClassic, TSB, ADIDA). `build_forecast_table` itera `FAMILIES` y corre cada grupo aparte; los nombres de modelo se derivan con `str(m)` (mismo alias que usa statsforecast para nombrar columnas).
4. **Selección de modelo** (`backtest_and_forecast`): cross-validation temporal (rolling origin, `N_WINDOWS=3`, `STEP_SIZE=4`), gana el menor **MASE no estacional** (`seasonality=1`, deliberado por series cortas/intermitentes).
5. **KPIs** (`calcular_kpis`): la existencia (nivel SKU) se **prorratea entre CDs** proporcional al histórico de ventas (`prorratear_existencia`). Deriva DOH/WOS/MOH (demanda diaria = `forecast_mensual_promedio / 30.44`), `estado_inventario` (Riesgo de quiebre si DOH < lead_time_dias / Sobre-stock si DOH > 120d / Normal en medio) y `cantidad_reorden` — cubre `LEAD_TIME_BUFFER=1.5` veces el lead time, redondeada al múltiplo de `pack`.

`H=4` (horizonte en meses), `SEASON_LENGTH=12`, `FREQ="1mo"` (offset **polars**, no pandas — `statsforecast` valida freq contra polars cuando el df es polars; usar `"MS"` u otro alias pandas revienta con `ValueError`) son constantes de pipeline.py.

## Convenciones de app.py

- **Todo en polars** (no pandas), incluso alimentando plotly con `.to_list()`.
- **i18n**: dict `STRINGS["es"|"en"]`; toda cadena visible sale de `TXT[...]`. Al añadir texto, agregar la llave en **ambos** idiomas.
- **Datos canónicos en español**: `estado_inventario`/`clasificacion` se guardan en español en el parquet; se traducen a la vista con `ESTADO_MAP`/`CLASE_MAP` según idioma. Los filtros comparan contra los valores mapeados (`estado_riesgo`, etc.), no contra literales.
- **`@st.cache_data` en `load()`**: no invalida por cambios en disco — ver nota de Commands arriba.
- **Filtros** (barra superior, no sidebar): Centro, Tipo de SKU (multiselect), Proveedor, Categoría. Los dos últimos usan `filtro_opcional()` — si la columna no existe en `resultados.parquet` el selector aparece deshabilitado en vez de desaparecer. Si `dimensiones.json` aporta columnas presentes en `resultados.parquet`, aparece además un multiselect "➕ Agregar filtros" (vacío por defecto) para sumar selectboxes dinámicos sobre esas dimensiones, reusando `filtro_opcional()` (dedupe por `label`, last-wins). Todo lo que se muestra en las 3 pestañas parte de `res_f` (resultado ya filtrado).
- **Carga de datos** (sidebar, expander "Cargar tus datos"): dos `file_uploader` + botón Procesar. También ofrece multiselects para elegir columnas extra ("dimensiones") de cada CSV — `key` por identidad de archivo (`nombre_tamaño`) para no crashear al cambiar de archivo. `procesar_archivos()` escribe `dimensiones.json` (siempre, incluso vacío, para no dejar dims de una carga anterior), luego sobrescribe `ventas_historicas.csv`/`inventario.csv` en disco y corre `pipeline.py` como subproceso (`sys.executable`, no asume `python` en PATH); si falla muestra `stderr` en la UI en vez de tumbar la app. No hace backup de los CSVs originales antes de sobrescribir.
- Paleta y layout de plotly centralizados arriba (`BG_*`, `ACCENT_*`, `PLOTLY_LAYOUT`, helper `axis()`). CSS inyectado en `inject_css()` fuerza texto blanco, oculta la barra superior de Streamlit (sin ocultar el botón de colapsar sidebar — usar `background: transparent`, no `display: none`, si se retoca) y estiliza el `file_uploader`.

## Nota

`.streamlit_run.sh` tiene una ruta absoluta hardcodeada de otra máquina — no usar tal cual.
