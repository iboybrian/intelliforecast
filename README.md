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

In the app's Secrets panel (or `.streamlit/secrets.toml` locally). The Zoho password stays there, not in the repo.

### Contact form and in-app feedback

Every beta request and every feedback note is emailed to **brianiboy@intellivet.tech** (To) and **brianjosue1900@gmail.com** (Cc). That send uses Zoho SMTP. The password is not in the repo. In the Streamlit Cloud app: Settings → Secrets:

```toml
[contact]
smtp_password = "zoho-app-password"
```

Zoho Mail → Settings → Security → App Passwords → generate one named IntelliForecast. Reboot the app after saving the secret. Until that password is there, Send opens a mail draft addressed to both inboxes with the answers filled in.

Optional, only if the Zoho account is not on smtp.zoho.com:

```toml
smtp_host = "smtp.zoho.com"
smtp_port = 587
smtp_user = "brianiboy@intellivet.tech"
```

`webhook_url` is an extra optional JSON POST. It is not required for the emails.

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
