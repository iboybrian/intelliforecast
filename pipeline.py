"""
Pipeline de forecast de demanda (demo).

Lee ventas_historicas.csv + inventario.csv, clasifica cada combinacion
SKU-centro_distribucion (Syntetos-Boylan-Croston), corre backtesting con
varios modelos estadisticos via statsforecast, selecciona el ganador por
MASE, genera forecast de 4 meses y calcula KPIs de inventario.

Ventas historicas vienen semanales pero se agregan a nivel mensual antes
de clasificar/pronosticar (ver aggregate_monthly).

Los CSV pueden traer cualquier nombre de columna: carga.json (escrito por app.py)
mapea destino -> origen. Sin carga.json usa los nombres canonicos en espanol.

Salida: resultados.parquet (tabla de resultados + KPIs) e historico.parquet
(serie historica larga, para graficar en el dashboard).
"""

import json
import sys
import tempfile
from datetime import date
from pathlib import Path

import polars as pl
from statsforecast import StatsForecast
from statsforecast.models import AutoETS, AutoARIMA, Theta, SeasonalNaive, CrostonClassic, TSB, ADIDA
from utilsforecast.losses import mase

H = 4                 # horizonte de forecast: 4 meses
SEASON_LENGTH = 12    # estacionalidad anual para datos mensuales
N_WINDOWS = 3         # ventanas de cross-validation (rolling origin)
STEP_SIZE = 4
FREQ = "1mo"          # offset polars (no pandas "MS")

# ADI/CV2 son los umbrales estandar de Syntetos-Boylan-Croston
ADI_THRESHOLD = 1.32
CV2_THRESHOLD = 0.49

LEAD_TIME_BUFFER = 1.5    # cantidad_reorden cubre 1.5x el lead time (colchon de seguridad)

# Techo de sanidad para 'cantidad'. Los exports del cliente traen filas con las columnas
# corridas (un campo de mas por comillas mal cerradas en la descripcion): ahi 'cantidad'
# termina siendo el numero de SKU, del orden de 1e9. Sin este corte 177 filas basura pesaban
# el 99.99% del volumen total y producian forecasts de 4.4e9 unidades.
# ponytail: umbral fijo. Si algun cliente vende de verdad >1M unidades/fila, mover a config
# antes que a deteccion de ancho de fila.
CANTIDAD_MAX = 1_000_000

MIN_TRAIN = 4             # piso de puntos de entrenamiento en la ventana mas temprana del CV
# series con menos de esto no alcanzan para el rolling origin -> forecast_corto()
MIN_PERIODOS = H + STEP_SIZE * (N_WINDOWS - 1) + MIN_TRAIN

ETAPAS = 5                # etapas del pipeline; app.py parsea "[n/ETAPAS]" para la barra

# columnas requeridas por lado; el resto del CSV puede venir como dimension extra.
REQ = {
    "ventas": ["sku", "centro_distribucion", "fecha", "cantidad"],
    "inventario": ["sku", "existencia"],
}
# pack y lead_time_dias son opcionales: si el CSV no los trae (o el SKU no esta en
# inventario) se rellenan con esto, pisable desde la UI via carga.json["defaults"].
# OJO: un lead_time inventado produce un estado_inventario inventado — calibrar con el negocio.
INV_DEFAULTS = {"existencia": 0.0, "pack": 1.0, "lead_time_dias": 30.0}

# names se derivan con str(m) — es el mismo alias que statsforecast usa para nombrar columnas.
FAMILIES = {
    "regular": {
        "clases": ["Smooth", "Erratic"],
        "models": [AutoETS(season_length=SEASON_LENGTH), AutoARIMA(season_length=SEASON_LENGTH),
                   Theta(season_length=SEASON_LENGTH), SeasonalNaive(season_length=SEASON_LENGTH)],
    },
    "intermitente": {
        "clases": ["Intermittent", "Lumpy"],
        "models": [CrostonClassic(), TSB(alpha_d=0.2, alpha_p=0.2), ADIDA()],
    },
}


def etapa(n, texto):
    """Marcador de progreso. app.py lo parsea para mover la barra del panel de carga, y en
    terminal se lee igual que antes. flush: el hijo escribe a un pipe y bufferia por bloques,
    asi que sin esto las etapas llegan de golpe al final."""
    print(f"[{n}/{ETAPAS}] {texto}", flush=True)


def resumen_conteo(df, col):
    """Conteo por categoria en una linea. Un print(df) de polars son ~10 lineas de marco que
    en el panel de la UI tapan todo lo demas."""
    conteo = df.group_by(col).len().sort(col)
    return "  " + " · ".join(f"{c}: {n:,}" for c, n in conteo.iter_rows())


def load_config(path="carga.json"):
    """Mapeo de columnas + dimensiones elegidas en app.py. Sin archivo -> {} (compat con
    `python pipeline.py` a secas: mapeo identidad y dimensiones auto-descubiertas)."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _parse_fecha(lf, fmt, path):
    """Columna 'fecha' String -> Date. strict=False manda las ilegibles a null; aggregate_monthly
    las cuenta y avisa."""
    if fmt != "auto":
        return lf.with_columns(pl.col("fecha").str.to_date(fmt, strict=False))
    # "auto" = inferencia de polars: reconoce los formatos comunes, pero si no reconoce
    # NINGUNO levanta ComputeError en vez de dar null (ej. un periodo "2026-02"). Se prueba
    # sobre una muestra para fallar aca, con un mensaje accionable, y no a media agregacion.
    muestra = lf.select("fecha").head(200).collect()
    try:
        muestra.select(pl.col("fecha").str.to_date(strict=False))
    except pl.exceptions.ComputeError:
        ejemplos = muestra["fecha"].drop_nulls().head(3).to_list()
        raise SystemExit(f"{path}: no se pudo inferir el formato de fecha (ejemplos: {ejemplos}). "
                         f"Elegir el formato explicito al cargar los datos.")
    return lf.with_columns(pl.col("fecha").str.to_date(strict=False))


def scan_lado(path, cfg, requeridas, opcionales=()):
    """scan_csv + proyeccion segun el mapeo de la UI. -> (LazyFrame, dims).

    select(alias) en vez de rename: habilita projection pushdown (polars parsea solo las
    columnas mapeadas, no las 1.5M filas completas) y evita colisiones si el CSV ya trae
    un header con el nombre destino.

    infer_schema_length=0 -> todo entra como String. Los CSV del cliente traen columnas
    mixtas (100 filas con "1" y despues un "1 MUEBLES") y la inferencia de polars aborta la
    corrida entera por una columna que quiza solo viaja como dimension. Los pocos campos
    numericos se castean explicito y no-estricto donde se usan: 'cantidad' en
    aggregate_monthly, existencia/pack/lead_time_dias en _numericos_con_default."""
    fmt = cfg.get("formato_fecha") or "auto"
    lf = pl.scan_csv(path, infer_schema_length=0)
    disponibles = lf.collect_schema().names()          # lee solo el header
    mapa = {d: o for d, o in (cfg.get("columnas") or {}).items() if o in disponibles}
    for c in (*requeridas, *opcionales):               # nombre canonico en el CSV -> mapeo identidad
        if c in disponibles:
            mapa.setdefault(c, c)
    faltan = [c for c in requeridas if c not in mapa]
    if faltan:
        raise SystemExit(f"{path}: faltan columnas requeridas {faltan} (columnas del archivo: {disponibles})")
    # con config de la UI las dims son las elegidas; sin config, todo lo que sobra.
    candidatas = cfg.get("dimensiones") or [] if cfg.get("columnas") else disponibles
    dims = [d for d in candidatas if d in disponibles and d not in mapa.values()]
    lf = lf.select([pl.col(o).alias(d) for d, o in mapa.items()] + [pl.col(d) for d in dims])
    if "fecha" in mapa:
        lf = _parse_fecha(lf, fmt, path)
    return lf, dims


def load_data(cfg=None):
    cfg = cfg or {}
    lf_ventas, dims_v = scan_lado("ventas_historicas.csv", cfg.get("ventas", {}), REQ["ventas"])
    lf_inv, dims_i = scan_lado("inventario.csv", cfg.get("inventario", {}), REQ["inventario"],
                               opcionales=("centro_distribucion", "pack", "lead_time_dias"))
    inventario = lf_inv.collect()
    # mismas llaves como String que del lado ventas (ver aggregate_monthly): un tienda_id
    # numerico no cruzaria contra el centro_distribucion string de las series.
    inventario = inventario.with_columns(
        pl.col(c).cast(pl.String) for c in ("sku", "centro_distribucion") if c in inventario.columns
    )
    return lf_ventas, dims_v, inventario, dims_i


def aggregate_monthly(lf: pl.LazyFrame, dims: list) -> pl.DataFrame:
    """Suma cantidad por mes calendario (mes-inicio). Unico collect del lado ventas:
    despues de aca todo trabaja sobre n_series x n_meses, no sobre el CSV crudo."""
    mensual = (
        lf.with_columns(
            # llaves siempre string: un CSV con sku/centro numericos rompe el concat y el join.
            pl.col("sku", "centro_distribucion").cast(pl.String),
            pl.col("fecha").dt.truncate(FREQ),
            pl.col("cantidad").cast(pl.Float64, strict=False),
        )
        # cantidad ilegible o fuera de rango -> null, y se descarta al sumar. Los negativos SI
        # entran: son devoluciones reales y netean contra la demanda del mes.
        .with_columns(
            pl.when(pl.col("cantidad").abs() <= CANTIDAD_MAX).then(pl.col("cantidad")).alias("cantidad")
        )
        .with_columns((pl.col("sku") + "|" + pl.col("centro_distribucion")).alias("unique_id"))
        # las dims NUNCA van en la llave del group_by: partirian la serie en k filas por mes
        # y statsforecast pronosticaria basura sin avisar.
        .group_by(["unique_id", "sku", "centro_distribucion", "fecha"])
        .agg(pl.col("cantidad").sum(),
             pl.col("cantidad").null_count().alias("_descartadas"),
             *[pl.col(d).drop_nulls().first() for d in dims])
        .sort(["unique_id", "fecha"])
        .collect()
    )
    # las fechas ilegibles caen en un bucket null: se cuentan en la misma pasada, sin re-escanear.
    malas = mensual.filter(pl.col("fecha").is_null())["cantidad"].sum()
    if malas:
        print(f"AVISO: {malas:,.0f} unidades con fecha ilegible descartadas (revisar formato de fecha)")
    corruptas = mensual["_descartadas"].sum()
    if corruptas:
        print(f"AVISO: {corruptas:,} filas con cantidad ilegible o mayor a {CANTIDAD_MAX:,} "
              f"descartadas (probable fila corrida en el CSV de ventas)")
    return mensual.filter(pl.col("fecha").is_not_null()).drop("_descartadas")


def classify_demand(ventas: pl.DataFrame) -> pl.DataFrame:
    """ADI (intervalo promedio entre meses con demanda) y CV2 (sobre valores > 0)."""
    stats = ventas.group_by(["unique_id", "sku", "centro_distribucion"]).agg([
        pl.len().alias("n_periodos"),
        (pl.col("cantidad") > 0).sum().alias("n_con_demanda"),
        pl.col("cantidad").filter(pl.col("cantidad") > 0).mean().alias("media_nz"),
        pl.col("cantidad").filter(pl.col("cantidad") > 0).std(ddof=0).alias("std_nz"),
    ])
    stats = stats.with_columns([
        (pl.col("n_periodos") / pl.col("n_con_demanda")).alias("adi"),
        pl.when(pl.col("media_nz") > 0)
          .then((pl.col("std_nz") / pl.col("media_nz")) ** 2)
          .otherwise(0.0)
          .alias("cv2"),
    ])
    stats = stats.with_columns(
        pl.when((pl.col("adi") < ADI_THRESHOLD) & (pl.col("cv2") < CV2_THRESHOLD)).then(pl.lit("Smooth"))
          .when((pl.col("adi") < ADI_THRESHOLD) & (pl.col("cv2") >= CV2_THRESHOLD)).then(pl.lit("Erratic"))
          .when((pl.col("adi") >= ADI_THRESHOLD) & (pl.col("cv2") < CV2_THRESHOLD)).then(pl.lit("Intermittent"))
          .otherwise(pl.lit("Lumpy"))
          .alias("clasificacion")
    )
    stats = stats.with_columns((pl.col("n_periodos") < MIN_PERIODOS).alias("flag_serie_corta"))
    return stats.select(["unique_id", "sku", "centro_distribucion", "n_periodos", "flag_serie_corta",
                         "adi", "cv2", "clasificacion"])


def _mase_valido(col="mase"):
    """MASE null (escala 0 por train constante) o NaN nunca puede ganar el sort: polars ordena
    los null PRIMERO, asi que sin esto el peor modelo gana. Tambien evita que app.py reviente
    formateando un None con f'{mase:.2f}'."""
    return pl.col(col).fill_nan(None).fill_null(float("inf"))


def backtest_and_forecast(df_family: pl.DataFrame, models, model_names) -> pl.DataFrame:
    """Cross-validation temporal (rolling origin) + MASE + forecast final del ganador."""
    sf_df = df_family.rename({"fecha": "ds", "cantidad": "y"}).select(["unique_id", "ds", "y"])

    # n_jobs=-1: mismos numeros, ~3x mas rapido. fallback_model: si un modelo revienta en una
    # serie puntual, esa serie no tumba la corrida entera.
    sf = StatsForecast(models=models, freq=FREQ, n_jobs=-1,
                       fallback_model=SeasonalNaive(season_length=1))
    cv = sf.cross_validation(h=H, df=sf_df, n_windows=N_WINDOWS, step_size=STEP_SIZE)

    # MASE no estacional (seasonality=1): mas robusto que m=52 para series cortas/intermitentes.
    mase_per_cutoff = mase(df=cv, models=model_names, seasonality=1, train_df=sf_df,
                            id_col="unique_id", target_col="y", cutoff_col="cutoff", time_col="ds")
    mase_avg = mase_per_cutoff.group_by("unique_id").agg(
        [pl.col(m).mean().alias(m) for m in model_names]
    )

    mase_long = mase_avg.unpivot(index="unique_id", on=model_names,
                                  variable_name="modelo", value_name="mase")
    winners = (
        mase_long.with_columns(_mase_valido()).sort("mase")
        .group_by("unique_id", maintain_order=True).first()
        .rename({"modelo": "modelo_ganador"})
    )

    # refit final solo del modelo ganador de cada serie: el sf.forecast() sobre historia completa
    # es ~45% del wall clock y hoy fitea 4 modelos por serie para descartar 3. Mismos numeros.
    trozos = []
    for modelo, grupo in winners.group_by("modelo_ganador"):
        nombre = modelo[0] if isinstance(modelo, tuple) else modelo
        modelo_obj = next(m for m in models if str(m) == nombre)
        sub = sf_df.filter(pl.col("unique_id").is_in(grupo["unique_id"].implode()))
        sf_uno = StatsForecast(models=[modelo_obj], freq=FREQ, n_jobs=-1,
                               fallback_model=SeasonalNaive(season_length=1))
        trozos.append(sf_uno.forecast(h=H, df=sub).select(
            "unique_id", "ds", pl.col(nombre).alias("valor")))
    forecast_winner = pl.concat(trozos, how="vertical_relaxed")

    ancho = (
        forecast_winner.sort(["unique_id", "ds"])
        .with_columns(pl.col("ds").cum_count().over("unique_id").alias("mes_n"))
    )
    forecast_wide = (ancho.pivot(index="unique_id", on="mes_n", values="valor")
                     .rename({str(i): f"forecast_w{i}" for i in range(1, H + 1)}))
    fechas_wide = (ancho.pivot(index="unique_id", on="mes_n", values="ds")
                   .with_columns(pl.col(f"{i}").cast(pl.Date) for i in range(1, H + 1))
                   .rename({str(i): f"fecha_w{i}" for i in range(1, H + 1)}))

    return winners.join(forecast_wide, on="unique_id").join(fechas_wide, on="unique_id")


def forecast_corto(ventas: pl.DataFrame) -> pl.DataFrame:
    """Series con < MIN_PERIODOS meses: no alcanzan para el rolling origin (statsforecast
    revienta antes de instanciar el modelo). SeasonalNaive degenerado (season_length=1 = ultimo
    valor; la estacionalidad anual no es estimable con tan poca historia), en polars puro para
    que no pueda lanzar excepcion. MASE de holdout de 1 punto: NO es comparable con el MASE de
    3 ventanas/h=4 de las series largas — por eso existe flag_serie_corta."""
    train = pl.col("cantidad").slice(0, pl.max_horizontal(pl.len() - 1, pl.lit(1)))
    g = ventas.sort(["unique_id", "fecha"]).group_by("unique_id").agg(
        pl.col("cantidad").last().alias("y_test"),
        train.last().alias("valor"),
        train.diff().abs().mean().alias("escala"),
        pl.col("fecha").last().alias("ultima"),
    )
    return (
        g.with_columns(((pl.col("y_test") - pl.col("valor")).abs() / pl.col("escala")).alias("mase"))
        .with_columns(_mase_valido())
        .select("unique_id", pl.lit("SeasonalNaive").alias("modelo_ganador"), "mase",
                *[pl.col("valor").cast(pl.Float32).alias(f"forecast_w{i}") for i in range(1, H + 1)],
                *[pl.col("ultima").dt.offset_by(f"{i}mo").cast(pl.Date).alias(f"fecha_w{i}")
                  for i in range(1, H + 1)])
    )


def build_forecast_table(ventas: pl.DataFrame, clasif: pl.DataFrame) -> pl.DataFrame:
    resultados = []
    cortas = clasif.filter(pl.col("flag_serie_corta"))["unique_id"]
    if cortas.len():
        etapa(3, f"{cortas.len():,} series cortas (<{MIN_PERIODOS} meses) -> SeasonalNaive")
        resultados.append(forecast_corto(ventas.filter(pl.col("unique_id").is_in(cortas.implode()))))

    for fam, fam_cfg in FAMILIES.items():
        ids = clasif.filter(pl.col("clasificacion").is_in(fam_cfg["clases"])
                            & ~pl.col("flag_serie_corta"))["unique_id"]
        if ids.len():
            etapa(3, f"Backtesting {ids.len():,} series de familia {fam}...")
            sub = ventas.filter(pl.col("unique_id").is_in(ids.implode()))
            names = [str(m) for m in fam_cfg["models"]]
            resultados.append(backtest_and_forecast(sub, fam_cfg["models"], names))

    forecast_tabla = pl.concat(resultados, how="vertical_relaxed")
    # el inf que mete _mase_valido solo existe para que un MASE nulo no gane el sort. En la
    # salida es ruido (40% de las filas del cliente), rompe el xlsx y no dice nada: vuelve a
    # null, que en la UI se lee "no medible".
    forecast_tabla = forecast_tabla.with_columns(
        pl.when(pl.col("mase").is_finite()).then(pl.col("mase")).alias("mase")
    )
    return clasif.join(forecast_tabla, on="unique_id")


SALIDA_EXISTENCIA = ["sku", "centro_distribucion", "existencia_cd", "existencia_desconocida",
                     "pack", "lead_time_dias"]


def _numericos_con_default(df: pl.DataFrame, defaults) -> pl.DataFrame:
    """Castea existencia/pack/lead_time_dias a Float64 y rellena los huecos con su default.

    El CSV entra todo como String (ver scan_lado): el cast es no-estricto para que un "N/A"
    o un "1,234" caiga en el default en vez de tumbar la corrida. Se cuenta cuantos se
    perdieron: una columna entera ilegible da existencia 0 -> todo en "Riesgo de quiebre",
    que sin este aviso parece un problema del modelo y no del archivo."""
    presentes = {k: df[k].is_not_null().sum() for k in defaults if k in df.columns}
    # 'existencia' en blanco no es "cero unidades", es "sin registro en esa ubicacion" (el export
    # del cliente trae 36k de 50k filas vacias). Se marca ANTES de que el default 0 la vuelva
    # indistinguible de un quiebre real; los dos caminos de resolver_existencia_por_cd lo propagan.
    df = df.with_columns(
        (pl.col("existencia").cast(pl.Float64, strict=False).is_null()
         if "existencia" in df.columns else pl.lit(True)).alias("_sin_dato")
    )
    # una sola expresion cubre los dos huecos: columna nunca mapeada (pl.lit) y fila ausente
    # del inventario (el null que deja el left join).
    df = df.with_columns([
        (pl.col(k) if k in df.columns else pl.lit(v)).cast(pl.Float64, strict=False).alias(k)
        for k, v in defaults.items()
    ])
    for k, n in presentes.items():
        ilegibles = n - df[k].is_not_null().sum()
        if ilegibles:
            print(f"AVISO: {ilegibles:,} valores de '{k}' no son numericos -> default {defaults[k]}")
    return df.with_columns([pl.col(k).fill_null(v) for k, v in defaults.items()])


def _existencia_por_cd_directa(ventas_por_cd: pl.DataFrame, inventario: pl.DataFrame,
                               defaults) -> pl.DataFrame:
    """Inventario que ya viene por sku+CD: se matchea directo, sin repartir nada."""
    llaves = ["sku", "centro_distribucion"]
    # castear ANTES de agrupar: asi el aviso de valores ilegibles cuenta filas del archivo y no
    # grupos ya colapsados. Ademas garantiza que pack/lead_time_dias existan para el agg.
    filas = _numericos_con_default(inventario, defaults)
    # varias filas por sku-CD (bines/ubicaciones dentro de la tienda) se suman; sin esto el
    # join haria fan-out y duplicaria la combinacion en el parquet de resultados.
    inv = filas.group_by(llaves).agg(
        pl.col("existencia").sum(), pl.col("pack").first(), pl.col("lead_time_dias").first(),
        # solo es "sin registro" si TODAS las ubicaciones del sku-CD venian en blanco
        pl.col("_sin_dato").all().alias("existencia_desconocida"),
    )
    if inv.height < filas.height:
        print(f"AVISO: {filas.height - inv.height:,} filas de inventario duplicadas por "
              f"SKU-CD; se suma la existencia")

    cruzan = ventas_por_cd.join(inv, on=llaves, how="semi").height
    if cruzan < ventas_por_cd.height:
        print(f"AVISO: {ventas_por_cd.height - cruzan:,} de {ventas_por_cd.height:,} "
              f"combinaciones SKU-CD con ventas no estan en inventario -> existencia 0")
    if cruzan == 0:
        # tipico desajuste de formato de llave (id vs nombre de tienda, ceros a la izquierda):
        # sin este aviso el dashboard sale entero en "Riesgo de quiebre" sin un solo error.
        print(f"AVISO: NINGUNA combinacion SKU-CD cruzo contra el inventario. "
              f"Centros en ventas: {ventas_por_cd['centro_distribucion'].unique().head(5).to_list()} · "
              f"en inventario: {inv['centro_distribucion'].unique().head(5).to_list()}")

    # las combinaciones con ventas y sin fila de inventario quedan null -> default (existencia 0)
    directo = ventas_por_cd.join(inv, on=llaves, how="left").with_columns(
        [pl.col(k).fill_null(v) for k, v in defaults.items()]
        # sin fila de inventario tampoco hay dato: el null del left join tambien es "desconocida"
        + [pl.col("existencia_desconocida").fill_null(True)]
    )
    return directo.with_columns(pl.col("existencia").alias("existencia_cd")).select(SALIDA_EXISTENCIA)


def _existencia_por_cd_prorrateada(ventas_por_cd: pl.DataFrame, inventario: pl.DataFrame,
                                   defaults) -> pl.DataFrame:
    """Inventario a nivel SKU: se reparte entre los CDs proporcional al historico de ventas."""
    ventas_por_sku = ventas_por_cd.group_by("sku").agg(
        pl.col("ventas_totales_cd").sum().alias("ventas_totales_sku")
    )
    sin_inv = ventas_por_sku.join(inventario.select("sku"), on="sku", how="anti").height
    if sin_inv:
        print(f"AVISO: {sin_inv:,} SKU con ventas y sin registro en inventario -> existencia 0")

    prorrateo = ventas_por_cd.join(ventas_por_sku, on="sku").join(inventario, on="sku", how="left")
    prorrateo = _numericos_con_default(prorrateo, defaults)
    return prorrateo.with_columns(
        pl.when(pl.col("ventas_totales_sku") > 0)
          .then(pl.col("existencia") * pl.col("ventas_totales_cd") / pl.col("ventas_totales_sku"))
          .otherwise(pl.col("existencia") / pl.col("centro_distribucion").count().over("sku"))
          .alias("existencia_cd"),
        pl.col("_sin_dato").alias("existencia_desconocida"),
    ).select(SALIDA_EXISTENCIA)


def resolver_existencia_por_cd(ventas: pl.DataFrame, inventario: pl.DataFrame,
                               defaults) -> pl.DataFrame:
    """Existencia a nivel SKU-CD, que es el grano de resultados.parquet.

    Dos caminos segun lo que traiga el archivo de inventario:
      - con centro_distribucion -> join directo sku+CD, la existencia de cada tienda es la suya.
      - sin centro_distribucion -> se prorratea la existencia del SKU entre sus CDs.

    En los dos, join LEFT contra las ventas: una combinacion con ventas y sin fila de inventario
    conserva su forecast y entra con existencia 0 (-> Riesgo de quiebre). Dejarla null la
    etiquetaria "Normal" en silencio, porque un when() con condicion nula cae en el otherwise."""
    ventas_por_cd = ventas.group_by(["sku", "centro_distribucion"]).agg(
        pl.col("cantidad").sum().alias("ventas_totales_cd")
    )
    if "centro_distribucion" in inventario.columns:
        return _existencia_por_cd_directa(ventas_por_cd, inventario, defaults)
    return _existencia_por_cd_prorrateada(ventas_por_cd, inventario, defaults)


def calcular_kpis(tabla: pl.DataFrame, ventas: pl.DataFrame, inventario: pl.DataFrame, defaults) -> pl.DataFrame:
    existencias = resolver_existencia_por_cd(ventas, inventario, defaults)
    tabla = tabla.join(existencias, on=["sku", "centro_distribucion"])

    forecast_cols = [f"forecast_w{i}" for i in range(1, H + 1)]
    tabla = tabla.with_columns(
        pl.mean_horizontal(forecast_cols).clip(lower_bound=0).alias("forecast_mensual_promedio")
    )

    tabla = tabla.with_columns(
        (pl.col("forecast_mensual_promedio") / 30.44).alias("demanda_diaria_promedio")
    ).with_columns(
        pl.when((pl.col("demanda_diaria_promedio") > 1e-6) & ~pl.col("existencia_desconocida"))
          .then(pl.col("existencia_cd") / pl.col("demanda_diaria_promedio"))
          .otherwise(None)   # sin demanda o sin dato de existencia -> DOH no significa nada
          .alias("doh")
    ).with_columns([
        (pl.col("doh") / 7).alias("wos"),
        (pl.col("doh") / 30).alias("moh"),
    ])

    tabla = tabla.with_columns(
        # primero que nada: sin dato de existencia no hay KPI que valga. Meterlas en "Riesgo de
        # quiebre" inflaba esa lista con SKU que quiza estan surtidos, y el comprador reordenaba
        # a ciegas.
        pl.when(pl.col("existencia_desconocida")).then(pl.lit("Sin registro"))
          .when(pl.col("doh").is_null())
          .then(pl.when(pl.col("existencia_cd") > 0).then(pl.lit("Sobre-stock")).otherwise(pl.lit("Normal")))
          .when(pl.col("doh") < pl.col("lead_time_dias")).then(pl.lit("Riesgo de quiebre"))
          .when(pl.col("doh") > 120).then(pl.lit("Sobre-stock"))
          .otherwise(pl.lit("Normal"))
          .alias("estado_inventario")
    )

    tabla = tabla.with_columns(
        (pl.col("demanda_diaria_promedio") * pl.col("lead_time_dias") * LEAD_TIME_BUFFER).alias("demanda_lead_time")
    ).with_columns(
        pl.when(pl.col("pack") > 0)
          .then((pl.col("demanda_lead_time") / pl.col("pack")).ceil() * pl.col("pack"))
          .otherwise(0.0)
          .alias("cantidad_reorden")
    )

    return tabla


def unir_dimensiones(resultados, mensual, inventario, dims_v, dims_i):
    """Dimensiones extra al parquet de resultados. Las de ventas salen de `mensual` (no del CSV
    crudo: seria una segunda pasada sobre 1.5M filas) y se unen por sku+centro_distribucion, que
    es el grano de resultados — a nivel sku se tomaria el valor de un CD arbitrario.
    Nunca pisa una columna existente."""
    nuevas_v = [d for d in dims_v if d not in resultados.columns]
    if nuevas_v:
        for d in nuevas_v:
            variables = mensual.group_by(["sku", "centro_distribucion"]).agg(
                pl.col(d).n_unique().alias("n")).filter(pl.col("n") > 1).height
            if variables:
                print(f"AVISO: la dimension '{d}' tiene varios valores dentro de un mismo SKU-CD "
                      f"({variables:,} casos, dato transaccional?); se toma el primero")
        por_grupo = mensual.group_by(["sku", "centro_distribucion"]).agg(
            [pl.col(d).drop_nulls().first() for d in nuevas_v])
        resultados = resultados.join(por_grupo, on=["sku", "centro_distribucion"], how="left")

    nuevas_i = [d for d in dims_i if d not in resultados.columns]
    if nuevas_i:
        # con inventario por tienda hay que llavear por ambas: a nivel sku se tomaria el valor
        # de un CD arbitrario, igual que con las dimensiones de ventas de arriba.
        llaves_i = ["sku", "centro_distribucion"] if "centro_distribucion" in inventario.columns else ["sku"]
        resultados = resultados.join(inventario.select([*llaves_i, *nuevas_i]).unique(llaves_i),
                                     on=llaves_i, how="left")
    return resultados


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    cfg = load_config()
    defaults = {**INV_DEFAULTS, **{k: float(v) for k, v in cfg.get("defaults", {}).items()}}

    etapa(1, "Leyendo CSV y agregando a mensual...")
    lf_ventas, dims_v, inventario, dims_i = load_data(cfg)
    ventas = aggregate_monthly(lf_ventas, dims_v)
    print(f"  {ventas['unique_id'].n_unique():,} series · {ventas.height:,} filas mensuales · "
          f"{inventario.height:,} filas de inventario")

    etapa(2, "Clasificando demanda...")
    clasif = classify_demand(ventas)
    print(resumen_conteo(clasif, "clasificacion"))

    tabla = build_forecast_table(ventas, clasif)
    etapa(4, f"Calculando KPIs de {tabla.height:,} series...")

    resultados = calcular_kpis(tabla, ventas, inventario, defaults)
    resultados = unir_dimensiones(resultados, ventas, inventario, dims_v, dims_i)

    etapa(5, f"Resultados: {resultados.height:,} combinaciones SKU-centro")
    print(resumen_conteo(resultados, "estado_inventario"))

    resultados.write_parquet("resultados.parquet")
    ventas.write_parquet("historico.parquet")
    print("Guardado: resultados.parquet, historico.parquet")


def _check():
    """Self-check del ETL: mapeo de columnas, formato de fecha, agregacion mensual, dimension
    que no parte la serie, series cortas sin NaN, y MASE null que no gana."""
    crudo = ("Codigo,Bodega,FechaDoc,Unidades,Linea\n"
             "A,N,01/02/2024,5,X\n"
             "A,N,15/02/2024,7,X\n"
             "A,S,03/01/2024,1,\n"
             # fila corrida: 'Unidades' quedo con el numero de SKU. Sin el corte de CANTIDAD_MAX
             # esta sola fila pesa mas que todo el resto del archivo.
             "A,N,20/02/2024,4403000038,X\n")
    cfg = {"columnas": {"sku": "Codigo", "centro_distribucion": "Bodega",
                        "fecha": "FechaDoc", "cantidad": "Unidades"},
           "formato_fecha": "%d/%m/%Y", "dimensiones": ["Linea"]}
    with tempfile.TemporaryDirectory() as tmp:
        csv = Path(tmp) / "v.csv"
        csv.write_text(crudo, encoding="utf-8")
        lf, dims = scan_lado(csv, cfg, REQ["ventas"])
        assert dims == ["Linea"], dims
        mensual = aggregate_monthly(lf, dims)

    a = mensual.filter(pl.col("unique_id") == "A|N")
    # 01/02/2024 es 1-feb en DD/MM y 2-ene en MM/DD: con el formato equivocado las dos filas
    # de febrero caen en meses distintos y estos tres asserts se caen juntos.
    assert a["fecha"].to_list() == [date(2024, 2, 1)], a["fecha"].to_list()
    # 12 y no 4403000050: la fila corrida quedo fuera por CANTIDAD_MAX
    assert a["cantidad"].to_list() == [12.0], a["cantidad"].to_list()
    assert a.height == 1, "la dimension partio la serie"
    assert a["Linea"].to_list() == ["X"]

    corto = forecast_corto(mensual)
    assert corto["mase"].is_null().sum() == 0 and corto["mase"].is_nan().sum() == 0
    assert corto["forecast_w4"].null_count() == 0
    # con historia suficiente para un holdout, el MASE es finito: |20-12| / mean|diff|
    seis = pl.DataFrame({"unique_id": ["B"] * 6, "cantidad": [10.0, 12, 11, 13, 12, 20],
                         "fecha": [date(2024, m, 1) for m in range(1, 7)]})
    assert abs(forecast_corto(seis)["mase"][0] - 8 / 1.5) < 1e-9

    d = pl.DataFrame({"modelo": ["X", "Y"], "mase": [None, 2.0]})
    assert d.with_columns(_mase_valido()).sort("mase")["modelo"][0] == "Y", "el MASE null gano"

    _check_existencia_desconocida()

    _check_existencia()
    print("check OK")


def _check_existencia():
    """Los dos caminos de resolver_existencia_por_cd: join directo por CD vs prorrateo."""
    # un SKU vendido en 2 tiendas, con 3/4 de la venta en N.
    ventas = pl.DataFrame({
        "sku": ["A"] * 4, "centro_distribucion": ["N", "N", "S", "S"],
        "cantidad": [30.0, 30, 10, 10],
    })

    # --- camino directo: cada tienda se queda con SU existencia, no con una fraccion ---
    inv_cd = pl.DataFrame({"sku": ["A", "A"], "centro_distribucion": ["N", "S"],
                           "existencia": ["100", "7"]})
    r = resolver_existencia_por_cd(ventas, inv_cd, INV_DEFAULTS).sort("centro_distribucion")
    assert r.height == 2, f"fan-out del join: {r.height} filas"
    assert r["existencia_cd"].to_list() == [100.0, 7.0], r["existencia_cd"].to_list()

    # filas duplicadas por sku-CD se suman (varios bines dentro de la misma tienda)
    inv_dup = pl.DataFrame({"sku": ["A"] * 3, "centro_distribucion": ["N", "N", "S"],
                            "existencia": ["60", "40", "7"]})
    r = resolver_existencia_por_cd(ventas, inv_dup, INV_DEFAULTS).sort("centro_distribucion")
    assert r.height == 2 and r["existencia_cd"].to_list() == [100.0, 7.0], r.to_dicts()

    # combinacion con ventas y sin fila de inventario -> existencia 0, no null (seria "Normal")
    inv_falta = pl.DataFrame({"sku": ["A"], "centro_distribucion": ["N"], "existencia": ["100"]})
    r = resolver_existencia_por_cd(ventas, inv_falta, INV_DEFAULTS).sort("centro_distribucion")
    assert r["existencia_cd"].to_list() == [100.0, 0.0], r["existencia_cd"].to_list()

    # --- camino prorrateo: sin columna de CD, se reparte 120 segun la venta (75%/25%) ---
    inv_sku = pl.DataFrame({"sku": ["A"], "existencia": ["120"]})
    r = resolver_existencia_por_cd(ventas, inv_sku, INV_DEFAULTS).sort("centro_distribucion")
    assert r["existencia_cd"].to_list() == [90.0, 30.0], r["existencia_cd"].to_list()
    # y los defaults siguen entrando donde el archivo no trae la columna
    assert r["pack"].to_list() == [1.0, 1.0] and r["lead_time_dias"].to_list() == [30.0, 30.0]


def _check_existencia_desconocida():
    """Existencia en blanco != 0 unidades: tiene que salir marcada por los dos caminos."""
    ventas = pl.DataFrame({"sku": ["A", "A"], "centro_distribucion": ["N", "S"],
                           "cantidad": [30.0, 10.0]})

    # directo: N trae dato (aunque sea 0), S viene en blanco -> solo S es desconocida
    inv = pl.DataFrame({"sku": ["A", "A"], "centro_distribucion": ["N", "S"],
                        "existencia": ["0", None]})
    r = resolver_existencia_por_cd(ventas, inv, INV_DEFAULTS).sort("centro_distribucion")
    assert r["existencia_desconocida"].to_list() == [False, True], r.to_dicts()

    # una ubicacion con dato basta: no es desconocida aunque la otra venga vacia
    inv_mix = pl.DataFrame({"sku": ["A"] * 2, "centro_distribucion": ["N", "N"],
                            "existencia": [None, "40"]})
    r = resolver_existencia_por_cd(ventas, inv_mix, INV_DEFAULTS).sort("centro_distribucion")
    assert r.filter(pl.col("centro_distribucion") == "N")["existencia_desconocida"][0] is False
    # ...y la combinacion sin fila de inventario tampoco tiene dato
    assert r.filter(pl.col("centro_distribucion") == "S")["existencia_desconocida"][0] is True

    # prorrateo: sin columna de CD, el blanco a nivel SKU marca todos sus centros
    r = resolver_existencia_por_cd(ventas, pl.DataFrame({"sku": ["A"], "existencia": [None]}),
                                   INV_DEFAULTS)
    assert r["existencia_desconocida"].to_list() == [True, True], r.to_dicts()


if __name__ == "__main__":
    _check() if "--check" in sys.argv else main()
