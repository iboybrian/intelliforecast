"""
Recalibra 'existencia' en inventario.csv (a nivel SKU) para lograr una
distribucion de estado de inventario mas repartida en el demo:
~30% Normal, ~10% Sobre-stock, resto Riesgo de quiebre.

Usa el forecast ya calculado en resultados.parquet (demanda_diaria_promedio
por combinacion SKU-CD) para estimar, por SKU, la existencia total que
produce el DOH objetivo. Requiere haber corrido pipeline.py al menos una
vez antes (para tener resultados.parquet con demanda pronosticada).
"""

import random

import polars as pl

random.seed(42)

res = pl.read_parquet("resultados.parquet")
inv = pl.read_csv("inventario_original.csv")

por_sku = res.group_by("sku").agg([
    pl.col("demanda_diaria_promedio").sum().alias("demanda_diaria_total"),
    pl.col("lead_time_dias").first().alias("lead_time_dias"),
])
por_sku = por_sku.join(inv.select(["sku", "pack"]), on="sku").sort("sku")

skus = por_sku["sku"].to_list()
random.shuffle(skus)

n = len(skus)
# proporciones ajustadas a nivel SKU (mayores que el objetivo final) para
# compensar que no todas las combinaciones SKU-CD de un mismo SKU caen en
# la misma clase de estado (la demanda difiere entre CDs).
n_sobrestock = round(n * 0.07)
n_normal = round(n * 0.38)
n_riesgo = n - n_sobrestock - n_normal

target_clase = {}
for sku in skus[:n_sobrestock]:
    target_clase[sku] = "Sobre-stock"
for sku in skus[n_sobrestock:n_sobrestock + n_normal]:
    target_clase[sku] = "Normal"
for sku in skus[n_sobrestock + n_normal:]:
    target_clase[sku] = "Riesgo de quiebre"

rows = []
for row in por_sku.iter_rows(named=True):
    sku = row["sku"]
    lt = row["lead_time_dias"]
    demanda_total = max(row["demanda_diaria_total"], 0.01)
    clase = target_clase[sku]

    if clase == "Riesgo de quiebre":
        target_doh = random.uniform(0.3 * lt, 0.85 * lt)
    elif clase == "Normal":
        lo = lt * 1.15
        hi = 115
        if lo >= hi:
            lo, hi = lt * 1.05, lt * 1.15
        target_doh = random.uniform(lo, hi)
    else:  # Sobre-stock
        target_doh = random.uniform(135, 260)

    existencia = max(round(target_doh * demanda_total), row["pack"])
    rows.append({"sku": sku, "existencia": existencia, "target_clase": clase, "target_doh": round(target_doh, 1)})

nuevas = pl.DataFrame(rows)
print(nuevas.group_by("target_clase").len())

inv_nuevo = (
    inv.drop("existencia")
    .join(nuevas.select(["sku", "existencia"]), on="sku")
    .select(["sku", "existencia", "pack", "lead_time_dias"])
    .sort("sku")
)
inv_nuevo.write_csv("inventario.csv")
print("inventario.csv actualizado")
print(inv_nuevo.head())
