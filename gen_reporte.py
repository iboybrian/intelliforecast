"""Genera reporte_premiumpet.pdf (3 páginas) desde screenshots en assets/.
HTML autocontenido (imágenes base64) -> Chrome headless --print-to-pdf.
"""
import base64
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"
HTML_OUT = ROOT / "reporte_premiumpet.html"
PDF_OUT = ROOT / "reporte_premiumpet.pdf"

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

MESES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def b64(name):
    data = (ASSETS / name).read_bytes()
    return "data:image/png;base64," + base64.b64encode(data).decode()


def build_html():
    hoy = date.today()
    fecha = f"{hoy.day} de {MESES[hoy.month]} de {hoy.year}"
    logo = b64("premiumpet.png")
    dashboard = b64("dashboard.png")
    quiebre = b64("quiebre.png")
    exceso = b64("exceso.png")

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<style>
  @page {{ size: A4; margin: 0; }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  :root {{
    --navy: #0B2545;
    --navy-soft: #13315C;
    --gold: #C9A24B;
    --teal: #1E7A6F;
    --ink: #2E3844;
    --muted: #6B7683;
    --line: #E3E7EC;
  }}
  html {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  body {{
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    color: var(--ink);
    background: #fff;
  }}
  .page {{
    position: relative;
    width: 210mm;
    height: 297mm;
    padding: 20mm 22mm;
    page-break-after: always;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }}
  .page:last-child {{ page-break-after: auto; }}

  /* --- Header --- */
  .head {{
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    border-bottom: 2px solid var(--navy);
    padding-bottom: 9mm;
  }}
  .head .brandline {{ font-size: 8.5pt; letter-spacing: .14em; text-transform: uppercase; color: var(--muted); }}
  .head .prepared {{ margin-top: 3mm; font-size: 9pt; color: var(--navy); font-weight: 600; }}
  .head .date {{ margin-top: 1.5mm; font-size: 8.5pt; color: var(--muted); }}
  .head .logo {{ width: 26mm; height: 26mm; object-fit: contain; }}

  .head--mini {{ padding-bottom: 6mm; }}
  .head--mini .logo {{ width: 16mm; height: 16mm; }}
  .head--mini .brandline {{ font-size: 8pt; }}

  /* --- Titles --- */
  .kicker {{
    display: inline-block;
    margin-top: 14mm;
    font-size: 8.5pt;
    letter-spacing: .18em;
    text-transform: uppercase;
    color: var(--gold);
    font-weight: 700;
  }}
  h1 {{
    font-family: Georgia, "Times New Roman", serif;
    font-size: 25pt;
    line-height: 1.18;
    color: var(--navy);
    font-weight: 700;
    margin-top: 5mm;
    max-width: 150mm;
  }}
  h2 {{
    font-family: Georgia, "Times New Roman", serif;
    font-size: 21pt;
    line-height: 1.2;
    color: var(--navy);
    font-weight: 700;
    margin-top: 4mm;
    max-width: 155mm;
  }}
  .subtitle {{
    margin-top: 4mm;
    font-size: 12.5pt;
    color: var(--teal);
    font-weight: 600;
  }}
  .lead {{
    margin-top: 6mm;
    font-size: 11pt;
    line-height: 1.65;
    color: var(--ink);
    max-width: 158mm;
  }}
  .accent-rule {{
    width: 34mm;
    height: 3px;
    background: var(--gold);
    margin-top: 8mm;
  }}
  .weblink {{
    margin-top: 6mm;
    font-size: 10.5pt;
    line-height: 1.55;
    color: var(--ink);
    max-width: 158mm;
  }}
  .weblink a {{ color: var(--teal); font-weight: 700; text-decoration: none; border-bottom: 1px solid var(--teal); }}

  /* --- Figure --- */
  .figwrap {{
    margin-top: auto;
    padding-top: 12mm;
  }}
  .figure {{
    border: 1px solid var(--line);
    border-radius: 6px;
    box-shadow: 0 10px 30px rgba(11,37,69,0.12);
    overflow: hidden;
  }}
  .figure img {{ width: 100%; display: block; }}
  .caption {{
    margin-top: 4mm;
    font-size: 8.5pt;
    color: var(--muted);
    text-align: center;
    letter-spacing: .03em;
  }}

  /* --- Footer / CTA --- */
  .foot {{
    position: absolute;
    left: 22mm; right: 22mm; bottom: 14mm;
    font-size: 8pt;
    color: var(--muted);
    border-top: 1px solid var(--line);
    padding-top: 4mm;
    display: flex;
    justify-content: space-between;
  }}
  .cta {{
    margin-top: 10mm;
    background: var(--navy);
    color: #fff;
    border-radius: 8px;
    padding: 8mm 9mm;
    display: flex;
    gap: 7mm;
    align-items: center;
  }}
  .cta .bar {{ width: 4px; align-self: stretch; background: var(--gold); border-radius: 2px; }}
  .cta .label {{ font-size: 8.5pt; letter-spacing: .16em; text-transform: uppercase; color: var(--gold); font-weight: 700; }}
  .cta p {{ margin-top: 3mm; font-size: 10pt; line-height: 1.55; color: #EAF0F7; }}
</style>
</head>
<body>

<!-- ============ PÁGINA 1 ============ -->
<section class="page">
  <div class="head">
    <div>
      <div class="brandline">Reporte confidencial · IntelliForecast</div>
      <div class="prepared">Preparado exclusivamente para PremiumPet</div>
      <div class="date">{fecha}</div>
    </div>
    <img class="logo" src="{logo}" alt="PremiumPet">
  </div>

  <span class="kicker">Análisis ejecutivo</span>
  <h1>Análisis Ejecutivo de Reabasto y Pronóstico de Demanda</h1>
  <div class="subtitle">Visibilidad total y salud financiera de su inventario</div>
  <p class="lead">Un panorama en tiempo real diseñado para identificar exactamente
  dónde está estancado su capital y en qué SKUs existe un riesgo inminente de
  perder clientes por falta de producto.</p>
  <p class="weblink">Pueden acceder a la versión web de la herramienta a través de este URL:
  <a href="https://intelliforecast.streamlit.app/">https://intelliforecast.streamlit.app/</a></p>
  <div class="accent-rule"></div>

  <div class="figwrap">
    <div class="figure"><img src="{dashboard}" alt="Vista general del tablero"></div>
    <div class="caption">Panel de control — Vista general de salud de inventario y pronóstico</div>
  </div>

  <div class="foot">
    <span>PremiumPet · Reporte de reabasto</span>
    <span>Página 1 de 3</span>
  </div>
</section>

<!-- ============ PÁGINA 2 ============ -->
<section class="page">
  <div class="head head--mini">
    <div class="brandline">IntelliForecast · Preparado para PremiumPet</div>
    <img class="logo" src="{logo}" alt="PremiumPet">
  </div>

  <span class="kicker">Riesgo de quiebre</span>
  <h2>Prevención de Ventas Perdidas (Fugas de Capital)</h2>
  <p class="lead">El sistema de pronóstico detecta automáticamente qué productos
  (SKUs) están por agotarse antes de que suceda, calculando la fecha exacta de
  reorden basándose en el Lead Time de su proveedor para garantizar
  disponibilidad continua.</p>
  <div class="accent-rule"></div>

  <div class="figwrap">
    <div class="figure"><img src="{quiebre}" alt="Detección de riesgo de quiebre"></div>
    <div class="caption">Detección temprana de quiebre y cálculo de fecha de reorden por SKU</div>
  </div>

  <div class="foot">
    <span>PremiumPet · Reporte de reabasto</span>
    <span>Página 2 de 3</span>
  </div>
</section>

<!-- ============ PÁGINA 3 ============ -->
<section class="page">
  <div class="head head--mini">
    <div class="brandline">IntelliForecast · Preparado para PremiumPet</div>
    <img class="logo" src="{logo}" alt="PremiumPet">
  </div>

  <span class="kicker">Sobre-stock</span>
  <h2>Liberación de Capital Estancado y Sobre-stock</h2>
  <p class="lead">Identificamos de manera algorítmica el inventario con baja
  rotación (sobre-stock) para evitar compras innecesarias, optimizar el espacio
  en el centro de distribución y mejorar drásticamente su flujo de efectivo.</p>
  <div class="accent-rule"></div>

  <div class="figwrap">
    <div class="figure"><img src="{exceso}" alt="Análisis de sobre-stock"></div>
    <div class="caption">Identificación de capital estancado por baja rotación</div>
  </div>

  <div class="cta">
    <div class="bar"></div>
    <div>
      <div class="label">Siguiente paso</div>
      <p>Reporte generado para revisión interna de Gerencia y Operaciones. Para
      ver el sistema interactivo en vivo y adaptarlo a sus proveedores, responda
      a este correo para agendar una sesión de 10 minutos.</p>
    </div>
  </div>

  <div class="foot">
    <span>PremiumPet · Reporte de reabasto</span>
    <span>Página 3 de 3</span>
  </div>
</section>

</body>
</html>"""


def find_chrome():
    for c in CHROME_CANDIDATES:
        if Path(c).exists():
            return c
    return None


def main():
    HTML_OUT.write_text(build_html(), encoding="utf-8")
    print(f"HTML -> {HTML_OUT}")

    chrome = find_chrome()
    if not chrome:
        print("Chrome/Edge no encontrado. Abre el HTML e imprime a PDF manualmente.")
        return

    cmd = [
        chrome, "--headless", "--disable-gpu", "--no-sandbox",
        "--no-pdf-header-footer",
        f"--print-to-pdf={PDF_OUT}",
        HTML_OUT.as_uri(),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if PDF_OUT.exists():
        print(f"PDF  -> {PDF_OUT}")
    else:
        print("Fallo al generar PDF:", r.stderr[-500:], file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
