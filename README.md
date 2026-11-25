# Employee Happiness Awards (EHA) – Insights & Analysis Report Generator

Upload a virtual judging presentation recording to generate an official, executive-grade **EHA Insights & Analysis Report** across 6 standardized sections, download the full **transcript as `.txt`**, and optionally **email the report (PDF)** to any recipient.

Stack: FastAPI, `google-genai` (Gemini 3.8 Flash, JSON mode), fpdf2, Brevo API / Gmail SMTP, vanilla HTML5/CSS3/ES6.

## Report Structure (Fixed 6 Sections)

1. **Company Information**: Company Name, Award Category, Awards Edition, Industry, Employee Headcount, Year Established, Presenter Name & Designation.
2. **Executive Overview**: Presentation context, rationale, objectives, execution approach, and jury Q&A focus areas.
3. **Employee Initiatives & Practices**: Pillar-by-pillar analysis dynamically filtered by award category mapping (Attraction & Onboarding, Learning & Growth, Well-being, Leadership & Strategy, Culture, Retention & Exit).
4. **Key Findings & Impact**: Measurable outcomes & comparative metrics table, employee survey results, and progress against objectives (organisation-reported findings).
5. **Feedback & Next Steps**: Strict distinction between Jury Observations & Q&A discussions and AI-generated strategic recommendations for long-term sustainability.
6. **Conclusion**: Executive synthesis of key strengths, demonstrated achievements, and employee lifecycle pillar alignment.

## Project layout

```
app.py                  FastAPI server (serves UI, POST /generate-report, POST /send-report, S3 multipart)
pipeline.py             Shared pipeline: Gemini -> EHA JSON -> PDF -> cleanup (try/finally)
gemini_client.py        Upload video, wait for ACTIVE, prompt + EHA JSON schema normalization
gemini_prompt_file.txt  Official EHA Gemini prompt template
pdf_report.py           Unicode-safe EHA PDF generator with 6 sections, tables, logo, and footer
emailer.py              Email sender supporting Brevo API or Gmail SMTP
config.py               Category-to-pillar mappings, EHA constants, model configuration
static/                 Client-facing dashboard (index.html, styles.css, app.js)
fonts/                  Bundled Unicode fonts (Noto Sans, Noto Sans Devanagari)
temp/                   Temporary uploads/PDFs (auto-created, auto-cleaned)
```

## Setup (Windows / PowerShell)

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Open `.env` and fill in:

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Gemini API key from https://aistudio.google.com/apikey |
| `EMAIL_PROVIDER` | `brevo` (default) or `gmail` |
| `SENDER_EMAIL` | Sender address (defaults to `rk26.ftw@gmail.com`) |
| `BREVO_API_KEY` | Brevo API key from https://app.brevo.com/settings/keys/api (when using `brevo`) |
| `GMAIL_APP_PASSWORD` | 16-char Gmail App Password from https://myaccount.google.com/apppasswords (when using `gmail`) |
| `SENDER_NAME` *(optional)* | Sender display name (default `Video Insights`) |
| `GEMINI_MODEL` *(optional)* | Defaults to `gemini-3.8-flash` (also editable in `config.py`) |

(macOS/Linux: `source venv/bin/activate` and `cp .env.example .env`.)

## Run the web app

```powershell
python app.py
```

Open **http://localhost:8000**, choose a video, and click **Generate Report**.
Once the report appears, you can:
1. Click **Download Report (PDF)** to save the formatted PDF.
2. Click **Download Transcript (.txt)** to save the full UTF-8 transcript.
3. Enter a recipient email under **Send report by email** and click the envelope icon (or press Enter) to email the PDF from `SENDER_EMAIL`.

## Run the test script (sample video, no browser)

```powershell
python test_pipeline.py                       # analyse + build PDF, keeps PDF in temp/
python test_pipeline.py --email you@site.com  # also email the PDF to that address
```

The script finds the first video in the project root (e.g. `sample_meeting.mp4`), copies it into `temp/`, and works only on that copy. **The original is never modified or deleted.**

## Notes & troubleshooting

- **Cleanup:** the temp video copy, the temp PDF (for web requests), and the Gemini remote file are always deleted (`try/finally`), and deletion is restricted to files inside `temp/`.
- **Brevo IP restriction (HTTP 401):** if Brevo rejects requests with an "unrecognised IP address" error, deactivate IP blocking at https://app.brevo.com/security/authorised_ips (home ISPs rotate IPv6 addresses), or set `EMAIL_PROVIDER=gmail` with a `GMAIL_APP_PASSWORD`.
- **Brevo sender verification:** ensure `SENDER_EMAIL` (`rk26.ftw@gmail.com`) is verified under Brevo -> Senders, Domains & Dedicated IPs -> Senders.
- **Model errors (404 / not found):** set `GEMINI_MODEL` in `.env` to a model available to your key.
- **Timeouts:** large videos may take minutes; adjust `FILE_PROCESSING_TIMEOUT_S` in `config.py`.
