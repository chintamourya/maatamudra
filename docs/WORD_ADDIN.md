# Maatamudra for Word (task-pane add-in)

Review an agreement without leaving Word. The add-in reads the open document, sends it to the Maatamudra backend,
and shows clause-level concerns, failed term checks and missing basic clauses. For any concern you can:

- **Show in document** (jumps to the clause)
- **Add comment** (or add all concerns as comments in one click)
- **Suggest balanced rewrite**, then **Apply as tracked change**. The edit lands as a normal Word revision you can accept or reject.

A rewrite that introduces a number, amount or date not present in your clause is blocked from applying (same
number-integrity rule as the main app).

## How it is wired

| Piece | File |
|---|---|
| Task pane UI | `backend/addin/taskpane.html`, `taskpane.css`, `taskpane.js` |
| Office manifest template | `backend/addin/manifest.template.xml` (served filled-in at `/addin/manifest.xml`) |
| Backend routes | `backend/app/addin.py` (`/addin/*` static files, manifest, `POST /api/addin/rewrite`) |
| Review | existing `POST /api/upload/analyze` (text mode) |

The add-in is served by the same FastAPI app, so **deploying the container deploys the add-in** and no CORS change is needed.

## Install (sideload) for the demo

Word add-ins must be served over **HTTPS**. Your deployed Azure URL already is. Then:

**Word on the web (easiest for a screen recording)**
1. Open `https://<your-deployed-url>/addin/manifest.xml` and save the file as `manifest.xml`.
2. In Word on the web open a document, then **Home → Add-ins → More Settings → Upload My Add-in** (or Insert → Add-ins), and choose that file.
3. A **Review agreement** button appears on the Home tab.

**Word desktop (Windows)**: put `manifest.xml` in a folder, share the folder, add it under
*File → Options → Trust Center → Trusted Add-in Catalogs*, then *Insert → My Add-ins → Shared Folder*.
**Word desktop (Mac)**: copy `manifest.xml` into `~/Library/Containers/com.microsoft.Word/Data/Documents/wef`.

**Local testing**: run the backend, expose it with an HTTPS tunnel (`ngrok http 8000` or `cloudflared tunnel --url http://localhost:8000`),
and open `<tunnel-url>/addin/manifest.xml` to get a manifest pointing at the tunnel.

**No Word at hand?** Open `https://<your-deployed-url>/addin/taskpane.html` in a browser. It switches to a paste-text mode so you can test the review flow.

## Demo flow (60 seconds)
1. Open `samples/freelance_service.docx` (or any agreement) in Word.
2. Click **Review agreement**, wait for the analysis.
3. Click a concern, then **Show in document**.
4. **Suggest balanced rewrite**, then **Apply as tracked change**, and show the revision in the Review tab.

## Limits (say these out loud, judges like honesty)
- The add-in reads paragraphs, so scanned or image-only documents are not supported here (the web app has OCR).
- Documents over about 60,000 characters are truncated for analysis.
- If you edit the document after reviewing, run the review again so clause positions stay accurate.
- The backend has no authentication yet. Use synthetic or redacted agreements on a public demo.
- Findings are review prompts, not legal advice.
