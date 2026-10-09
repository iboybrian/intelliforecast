"""Genera el demo público: CSVs sintéticos + parquets de forecast.

Todo lo que escribe vive en demo/. No toca ventas_historicas.csv, inventario.csv
ni los parquets del cliente. Los nombres (DEMO-*, DC-NORTH, Acme Sample Supply…)
son ficticios a propósito.

    python demo/generar_muestra.py          # regenera CSVs, corre pipeline.py, verifica
    python demo/generar_muestra.py --check  # solo verifica los parquets ya generados
"""

import csv
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
DEMO = Path(__file__).resolve().parent

PROVEEDORES = ("Acme Sample Supply", "Northwind Demo Parts", "Contoso Fictional Co")
CATEGORIAS = ("Fasteners", "Widgets", "Spares")
CENTROS = ("DC-NORTH", "DC-SOUTH", "DC-WEST")

MESES = [date(anio, mes, 1) for anio in (2024, 2025) for mes in range(1, 13)]


def _meses(n, ultimos=False):
    return MESES[-n:] if ultimos else MESES[:n]


def _cantidades(patron, n):
    """Serie mensual determinista. Los ceros van explícitos: sin esa fila el mes
    no existe y una serie intermitente se clasificaría como si vendiera siempre."""
    if patron == "flat100":
        return [100 + ((i % 5) - 2) for i in range(n)]
    if patron == "flat80":
        return [80 + (i % 3) - 1 for i in range(n)]
    if patron == "flat90":
        return [90 + (i % 4) - 1 for i in range(n)]
    if patron == "flat95":
        return [95 + (i % 3) for i in range(n)]
    if patron == "flat150":
        return [150 + ((i % 5) - 2) for i in range(n)]
    if patron == "flat60":
        return [60 + (i % 3) for i in range(n)]
    if patron == "flat40":
        return [40 + (i % 4) for i in range(n)]
    if patron == "flat30":
        return [30 + (i % 3) for i in range(n)]
    if patron == "erratic":
        return [20 if i % 2 == 0 else 220 for i in range(n)]
    if patron == "intermittent":
        return [30 if i % 3 == 0 else 0 for i in range(n)]
    if patron == "lumpy":
        picos = {0: 8, 4: 120, 9: 15, 14: 200, 19: 12, 23: 90}
        return [picos.get(i, 0) for i in range(n)]
    if patron == "seasonal":
        # onda anual suave, siempre con venta: sigue siendo Suave, no intermitente
        return [int(70 + 40 * (1 if (i % 12) in (10, 11, 0, 1) else 0) + (i % 3)) for i in range(n)]
    raise ValueError(patron)


# existencia None = celda en blanco (Sin registro). en_inventario False = sin fila.
SERIES = [
    # sku, centro, proveedor, categoria, patron, meses, existencia, pack, lead, en_inventario
    ("DEMO-BOLT-AURORA", "DC-NORTH", PROVEEDORES[0], CATEGORIAS[0], "flat100", 24, 5, 10, 90, True),
    ("DEMO-BOLT-AURORA", "DC-SOUTH", PROVEEDORES[0], CATEGORIAS[0], "flat90", 24, 15000, 10, 21, True),
    ("DEMO-WIDGET-BOREAL", "DC-NORTH", PROVEEDORES[1], CATEGORIAS[1], "flat95", 24, 180, 5, 14, True),
    ("DEMO-WIDGET-BOREAL", "DC-WEST", PROVEEDORES[1], CATEGORIAS[1], "seasonal", 24, 300, 5, 21, True),
    ("DEMO-GAUGE-CINDER", "DC-SOUTH", PROVEEDORES[2], CATEGORIAS[2], "erratic", 24, 500, 6, 30, True),
    ("DEMO-SPOOL-DRIFT", "DC-WEST", PROVEEDORES[0], CATEGORIAS[1], "flat100", 24, 200, 4, 15, True),
    ("DEMO-LATCH-EMBER", "DC-NORTH", PROVEEDORES[1], CATEGORIAS[0], "intermittent", 24, 40, 1, 21, True),
    ("DEMO-HINGE-FROST", "DC-SOUTH", PROVEEDORES[2], CATEGORIAS[2], "lumpy", 24, 100, 2, 30, True),
    ("DEMO-NOZZLE-GALE", "DC-WEST", PROVEEDORES[0], CATEGORIAS[2], "flat150", 24, 8, 12, 60, True),
    ("DEMO-PIN-HARBOR", "DC-NORTH", PROVEEDORES[1], CATEGORIAS[1], "flat80", 24, 20000, 8, 14, True),
    ("DEMO-VALVE-IRIS", "DC-SOUTH", PROVEEDORES[2], CATEGORIAS[0], "flat40", 8, 70, 1, 20, True),
    ("DEMO-KIT-JUNIPER", "DC-WEST", PROVEEDORES[0], CATEGORIAS[1], "flat60", 24, None, 1, 30, True),
    ("DEMO-BRACKET-KELP", "DC-NORTH", PROVEEDORES[1], CATEGORIAS[2], "flat30", 24, None, 1, 30, False),
]


def _escribir_csvs():
    ventas = DEMO / "ventas_sinteticas.csv"
    inventario = DEMO / "inventario_sintetico.csv"
    with ventas.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sku", "centro_distribucion", "fecha", "cantidad", "proveedor", "categoria", "origen_dato"])
        for sku, cd, prov, cat, patron, n, *_resto in SERIES:
            meses = _meses(n, ultimos=(n < 24))
            for mes, cant in zip(meses, _cantidades(patron, n)):
                w.writerow([sku, cd, mes.isoformat(), cant, prov, cat, "sintetico"])
    with inventario.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sku", "centro_distribucion", "existencia", "pack", "lead_time_dias"])
        for sku, cd, _prov, _cat, _patron, _n, exist, pack, lead, en_inv in SERIES:
            if not en_inv:
                continue
            w.writerow([sku, cd, "" if exist is None else exist, pack, lead])
    _escribir_plantillas()
    return ventas, inventario


def _escribir_plantillas():
    """Ejemplo corto para descargar desde la landing. Mismos headers que el pipeline espera."""
    (DEMO / "plantilla_ventas.csv").write_text(
        "sku,centro_distribucion,fecha,cantidad,proveedor,categoria\n"
        "DEMO-BOLT-AURORA,DC-NORTH,2024-01-01,102,Acme Sample Supply,Fasteners\n"
        "DEMO-BOLT-AURORA,DC-NORTH,2024-02-01,98,Acme Sample Supply,Fasteners\n"
        "DEMO-WIDGET-BOREAL,DC-SOUTH,2024-01-01,40,Northwind Demo Parts,Widgets\n"
        "DEMO-LATCH-EMBER,DC-WEST,2024-03-01,0,Northwind Demo Parts,Fasteners\n",
        encoding="utf-8",
    )
    (DEMO / "plantilla_inventario.csv").write_text(
        "sku,centro_distribucion,existencia,pack,lead_time_dias\n"
        "DEMO-BOLT-AURORA,DC-NORTH,30,10,21\n"
        "DEMO-WIDGET-BOREAL,DC-SOUTH,800,6,14\n"
        "DEMO-KIT-JUNIPER,DC-WEST,,1,30\n",
        encoding="utf-8",
    )


def _correr_pipeline(ventas: Path, inventario: Path):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        shutil.copy(ventas, tmp / "ventas_historicas.csv")
        shutil.copy(inventario, tmp / "inventario.csv")
        # sin carga.json: mapeo identidad. No se lee el carga.json del cliente.
        subprocess.check_call([sys.executable, str(ROOT / "pipeline.py")], cwd=tmp)
        shutil.copy(tmp / "resultados.parquet", DEMO / "resultados.parquet")
        shutil.copy(tmp / "historico.parquet", DEMO / "historico.parquet")


def verificar():
    res = pl.read_parquet(DEMO / "resultados.parquet")
    hist = pl.read_parquet(DEMO / "historico.parquet")
    skus = set(res["sku"].unique().to_list())
    assert skus and all(s.startswith("DEMO-") for s in skus), skus
    assert set(res["centro_distribucion"].unique()) <= set(CENTROS)
    assert set(res["proveedor"].unique()) <= set(PROVEEDORES)
    assert set(res["categoria"].unique()) <= set(CATEGORIAS)
    estados = set(res["estado_inventario"].unique().to_list())
    for requerido in ("Riesgo de quiebre", "Sobre-stock", "Normal", "Sin registro"):
        assert requerido in estados, (requerido, res.group_by("estado_inventario").len())
    assert hist["sku"].n_unique() == len(skus)
    assert "forecast_w1" in res.columns and res["forecast_w4"].null_count() == 0
    print(res.group_by("estado_inventario").len().sort("estado_inventario"))
    print(res.group_by("clasificacion").len().sort("clasificacion"))
    print(f"demo OK: {res.height} combinaciones, {hist.height} meses")


def main():
    if "--check" in sys.argv:
        verificar()
        return
    ventas, inventario = _escribir_csvs()
    print(f"CSVs sintéticos: {ventas.name}, {inventario.name}")
    _correr_pipeline(ventas, inventario)
    verificar()


if __name__ == "__main__":
    main()
