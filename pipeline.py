"""
Pipeline de forecast de demanda (demo).

Lee ventas_historicas.csv + inventario.csv, clasifica cada combinacion
SKU-centro_distribucion (Syntetos-Boylan-Croston), corre backtesting con
varios modelos estadisticos via statsforecast, selecciona el ganador por
MASE, genera forecast de 4 meses y calcula KPIs de inventario.

Ventas historicas vienen semanales pero se agregan a nivel mensual antes
de clasificar/pronosticar (ver aggregate_monthly).

Salida: resultados.parquet (tabla de resultados + KPIs) e historico.parquet
(serie historica larga, para graficar en el dashboard).
"""

import json
import sys

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

# columnas opcionales a nivel SKU en inventario.csv; se propagan a resultados si existen.
# (mecanismo separado de dimensiones.json/propagate_extra_dims mas abajo — no tocar este.)
OPTIONAL_SKU_COLS = ["proveedor", "categoria"]

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


def load_data():
    ventas = pl.read_csv("ventas_historicas.csv", try_parse_dates=True)
    ventas = ventas.with_columns(
        (pl.col("sku") + "|" + pl.col("centro_distribucion")).alias("unique_id")
    )
    inventario = pl.read_csv("inventario.csv")
    return ventas, inventario


def aggregate_monthly(ventas: pl.DataFrame) -> pl.DataFrame:
    """Suma cantidad semanal por mes calendario (mes-inicio)."""
    return (
        ventas.with_columns(pl.col("fecha").dt.truncate("1mo").alias("fecha"))
        .group_by(["unique_id", "sku", "centro_distribucion", "fecha"])
        .agg(pl.col("cantidad").sum())
        .sort(["unique_id", "fecha"])
    )


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
    return stats.select(["unique_id", "sku", "centro_distribucion", "adi", "cv2", "clasificacion"])


def backtest_and_forecast(df_family: pl.DataFrame, models, model_names) -> pl.DataFrame:
    """Cross-validation temporal (rolling origin) + MASE + forecast final del ganador."""
    sf_df = df_family.rename({"fecha": "ds", "cantidad": "y"}).select(["unique_id", "ds", "y"])

    sf = StatsForecast(models=models, freq=FREQ)
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
        mase_long.sort("mase").group_by("unique_id", maintain_order=True).first()
        .rename({"modelo": "modelo_ganador"})
    )

    forecast_all = sf.forecast(h=H, df=sf_df)
    forecast_long = forecast_all.unpivot(index=["unique_id", "ds"], on=model_names,
                                          variable_name="modelo", value_name="valor")
    forecast_winner = forecast_long.join(
        winners.select(["unique_id", "modelo_ganador"]),
        left_on=["unique_id", "modelo"], right_on=["unique_id", "modelo_ganador"], how="inner"
    )

    forecast_wide = (
        forecast_winner.sort(["unique_id", "ds"])
        .with_columns(pl.col("ds").cum_count().over("unique_id").alias("semana_n"))
        .pivot(index="unique_id", on="semana_n", values="valor")
        .rename({str(i): f"forecast_w{i}" for i in range(1, H + 1)})
    )
    fechas_wide = (
        forecast_winner.sort(["unique_id", "ds"])
        .with_columns(pl.col("ds").cum_count().over("unique_id").alias("semana_n"))
        .pivot(index="unique_id", on="semana_n", values="ds")
        .rename({str(i): f"fecha_w{i}" for i in range(1, H + 1)})
    )

    return winners.join(forecast_wide, on="unique_id").join(fechas_wide, on="unique_id")


def build_forecast_table(ventas: pl.DataFrame, clasif: pl.DataFrame) -> pl.DataFrame:
    resultados = []
    for fam_cfg in FAMILIES.values():
        ids = clasif.filter(pl.col("clasificacion").is_in(fam_cfg["clases"]))["unique_id"].to_list()
        if ids:
            fam = ventas.filter(pl.col("unique_id").is_in(ids))
            names = [str(m) for m in fam_cfg["models"]]
            resultados.append(backtest_and_forecast(fam, fam_cfg["models"], names))

    forecast_tabla = pl.concat(resultados, how="vertical")
    return clasif.join(forecast_tabla, on="unique_id")


def prorratear_existencia(ventas: pl.DataFrame, inventario: pl.DataFrame) -> pl.DataFrame:
    """Reparte la existencia a nivel SKU entre sus CDs, proporcional al historico de ventas."""
    ventas_por_cd = ventas.group_by(["sku", "centro_distribucion"]).agg(
        pl.col("cantidad").sum().alias("ventas_totales_cd")
    )
    ventas_por_sku = ventas_por_cd.group_by("sku").agg(
        pl.col("ventas_totales_cd").sum().alias("ventas_totales_sku")
    )
    prorrateo = ventas_por_cd.join(ventas_por_sku, on="sku").join(inventario, on="sku")
    prorrateo = prorrateo.with_columns(
        pl.when(pl.col("ventas_totales_sku") > 0)
          .then(pl.col("existencia") * pl.col("ventas_totales_cd") / pl.col("ventas_totales_sku"))
          .otherwise(pl.col("existencia") / pl.col("centro_distribucion").count().over("sku"))
          .alias("existencia_prorrateada")
    )
    return prorrateo.select(["sku", "centro_distribucion", "existencia_prorrateada", "pack", "lead_time_dias"])


def calcular_kpis(tabla: pl.DataFrame, ventas: pl.DataFrame, inventario: pl.DataFrame) -> pl.DataFrame:
    prorrateo = prorratear_existencia(ventas, inventario)
    tabla = tabla.join(prorrateo, on=["sku", "centro_distribucion"])

    forecast_cols = [f"forecast_w{i}" for i in range(1, H + 1)]
    tabla = tabla.with_columns(
        pl.mean_horizontal(forecast_cols).clip(lower_bound=0).alias("forecast_mensual_promedio")
    )

    tabla = tabla.with_columns(
        (pl.col("forecast_mensual_promedio") / 30.44).alias("demanda_diaria_promedio")
    ).with_columns(
        pl.when(pl.col("demanda_diaria_promedio") > 1e-6)
          .then(pl.col("existencia_prorrateada") / pl.col("demanda_diaria_promedio"))
          .otherwise(None)
          .alias("doh")
    ).with_columns([
        (pl.col("doh") / 7).alias("wos"),
        (pl.col("doh") / 30).alias("moh"),
    ])

    tabla = tabla.with_columns(
        pl.when(pl.col("doh").is_null())
          .then(pl.when(pl.col("existencia_prorrateada") > 0).then(pl.lit("Sobre-stock")).otherwise(pl.lit("Normal")))
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


def load_dim_config(path="dimensiones.json"):
    """Dimensiones extra elegidas en app.py al subir CSVs. Sin archivo -> [] (compat con
    `python pipeline.py` a secas, sin pasar por app.py)."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def propagate_extra_dims(resultados, ventas_raw, inventario, config):
    """Une columnas extra elegidas en la UI. Nunca pisa una columna ya presente en
    resultados (mismo footgun silencioso de .join/.with_columns que con OPTIONAL_SKU_COLS).
    Origen ventas: join por sku+centro_distribucion (el valor puede variar por CD).
    Origen inventario: join por sku (mismo patron que OPTIONAL_SKU_COLS)."""
    for entry in config:
        col, origen = entry["columna"], entry["origen"]
        src = ventas_raw if origen == "ventas" else inventario
        if col not in src.columns or col in resultados.columns:
            continue
        if origen == "ventas":
            por_grupo = src.group_by(["sku", "centro_distribucion"]).agg(pl.col(col).first())
            resultados = resultados.join(por_grupo, on=["sku", "centro_distribucion"], how="left")
        else:
            por_sku = src.select(["sku", col]).unique("sku")
            resultados = resultados.join(por_sku, on="sku", how="left")
    return resultados


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ventas, inventario = load_data()
    ventas_raw = ventas  # antes de aggregate_monthly, para dims extra de origen "ventas"
    ventas = aggregate_monthly(ventas)
    print(f"Ventas (mensual): {ventas.shape}, Inventario: {inventario.shape}")

    clasif = classify_demand(ventas)
    print("Clasificacion de demanda:")
    print(clasif.group_by("clasificacion").len().sort("clasificacion"))

    tabla = build_forecast_table(ventas, clasif)
    print(f"Tabla de forecast: {tabla.shape}")

    resultados = calcular_kpis(tabla, ventas, inventario)

    presentes = [c for c in OPTIONAL_SKU_COLS if c in inventario.columns]
    if presentes:
        resultados = resultados.join(inventario.select(["sku", *presentes]).unique("sku"), on="sku", how="left")

    # OPTIONAL_SKU_COLS que no vienen en inventario pero sí en ventas (p.ej. proveedor a nivel venta).
    en_ventas = [c for c in OPTIONAL_SKU_COLS if c not in inventario.columns and c in ventas_raw.columns]
    if en_ventas:
        prov = ventas_raw.group_by("sku").agg([pl.col(c).first() for c in en_ventas])
        resultados = resultados.join(prov, on="sku", how="left")

    resultados = propagate_extra_dims(resultados, ventas_raw, inventario, load_dim_config())

    print(f"Resultados finales: {resultados.shape}")
    print(resultados.group_by("estado_inventario").len())

    resultados.write_parquet("resultados.parquet")
    ventas.select(["unique_id", "sku", "centro_distribucion", "fecha", "cantidad"]).write_parquet("historico.parquet")
    print("Guardado: resultados.parquet, historico.parquet")


if __name__ == "__main__":
    main()
