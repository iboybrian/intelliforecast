# IntelliForecast

Monthly demand forecast and inventory replenishment. The public app has two pages:

- **Home** explains the product, lists the CSV columns, and offers a sample demo.
- **Forecast** is the dashboard (overview, stockout risk, overstock).

The interface is Spanish and English. The sidebar switch sets the language.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

**Try the demo** on Home opens Forecast with bundled synthetic data (`demo/resultados.parquet`). No account. The SKUs, centers and suppliers are fictional (`DEMO-*`, `DC-NORTH`, `Acme Sample Supply`, …).

**I already have access** uses the existing client login. That path still reads `resultados.parquet` / `historico.parquet` in the repo root and is unchanged.

Regenerate the sample (does not touch the client CSVs or parquets):

```bash
python demo/generar_muestra.py
python demo/generar_muestra.py --check
```

## Secrets on Streamlit Community Cloud

In the app's Secrets panel (or `.streamlit/secrets.toml` locally). Nothing below is hardcoded in the app.

### Contact form and in-app feedback

Both the beta-tester form and the Forecast feedback button POST the same JSON payload. If `webhook_url` is missing or the POST fails, the visitor sees `email` and a mailto link with their answers filled in. If neither is set, the form says so and does not invent an address.

```toml
[contact]
email = "team@example.com"
# Optional. Any HTTPS endpoint that accepts a JSON POST.
# http is accepted only for 127.0.0.1 / localhost, so you can try it locally.
webhook_url = "https://script.google.com/macros/s/XXXX/exec"
```

`email` alone is enough for the fallback. Set `webhook_url` when you want submissions stored automatically.

Payload fields:

- `kind`: `beta_access` or `feedback`
- `submitted_at`, `lang` (`es` / `en`), `modo` (`demo` / `cliente` / `visita`)
- beta: `nombre`, `email`, `empresa`, `rol`, `industria`, `n_skus`, `n_centros`, `mensaje`
- feedback: `email` (may be empty), `que_funciono`, `que_no_funciono`, `vista`

A redirect in the 3xx range counts as delivered. Google Apps Script web apps answer with 302 after they have already appended the row.

Example Apps Script (deploy as a web app, access "Anyone", and put that URL in `webhook_url`):

```javascript
function doPost(e) {
  var sheet = SpreadsheetApp.openById("SHEET_ID").getSheets()[0];
  var data = JSON.parse(e.postData.contents);
  var keys = ["submitted_at","kind","lang","modo","nombre","email","empresa","rol",
              "industria","n_skus","n_centros","mensaje","que_funciono","que_no_funciono","vista"];
  sheet.appendRow(keys.map(function (k) { return data[k] || ""; }));
  return ContentService.createTextOutput("ok");
}
```

A Slack incoming webhook, Zapier, or Make URL works the same way: it just has to accept the JSON POST.

### Client login

Unchanged. One block per client, password never stored in clear text:

```bash
python auth.py nuevo <usuario>
python auth.py --check
```

Paste the printed block:

```toml
[users.nombre]
hash = "scrypt$..."
url = "app_pages/forecast.py"
```

## What the public demo does not do

Uploading CSVs from the demo is turned off. The upload modal overwrites `ventas_historicas.csv` and `inventario.csv` on the app disk, which on Community Cloud is the client data. Beta access is the path for someone who wants to try their own files.
