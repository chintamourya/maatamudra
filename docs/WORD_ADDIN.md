# Maatamudra for Word (task-pane add-in)

Review an agreement without leaving Word. The add-in reads the open document, sends it to the Maatamudra backend,
and shows clause-level concerns, failed term checks and missing basic clauses. For any concern you can:

- **Show in document** (jumps to the clause)
- **Add comment** (or add all concerns as comments in one click)
- **Suggest balanced rewrite**, then **Apply as tracked change**. The edit lands as a normal Word revision you can accept or reject.

A rewrite that introduces a number, amount or date not present in your clause is blocked from applying (same
number-integrity rule as the main app).

## Install (sideload) for the demo

The Maatamudra demo must be available over **HTTPS**. Ask the demo organizer for its URL, then:

**Word on the web (easiest for a screen recording)**
1. Open `<demo-url>/addin/manifest.xml` and save the file as `manifest.xml`.
2. In Word on the web open a document, then **Home → Add-ins → More Settings → Upload My Add-in** (or Insert → Add-ins), and choose that file.
3. A **Review agreement** button appears on the Home tab.

**Word desktop (Windows)**: put `manifest.xml` in a folder, share the folder, add it under
*File → Options → Trust Center → Trusted Add-in Catalogs*, then *Insert → My Add-ins → Shared Folder*.
**Word desktop (Mac)**: copy `manifest.xml` into `~/Library/Containers/com.microsoft.Word/Data/Documents/wef`.

**No Word at hand?** Open `<demo-url>/addin/taskpane.html` in a browser. It switches to a paste-text mode so you can try the review flow.

## How to use it

1. Open a supported agreement in Word and select **Review agreement** on the Home tab.
2. Wait for the analysis, then select a concern to see its details.
3. Choose **Show in document** to jump to the relevant text, or add a comment to record the concern.
4. To revise a clause, choose **Suggest balanced rewrite**, review the proposed wording, then select **Apply as tracked change**.
5. Use Word's Review tab to accept or reject the change. If you edit the document, run the analysis again.

## Quick demo

1. Open `samples/freelance_service.docx` (or any agreement) in Word.
2. Click **Review agreement**, wait for the analysis.
3. Click a concern, then **Show in document**.
4. **Suggest balanced rewrite**, then **Apply as tracked change**, and show how to accept or reject the revision in the Review tab.

## Limits (say these out loud, judges like honesty)
- The add-in reads paragraphs, so scanned or image-only documents are not supported here (the web app has OCR).
- Documents over about 60,000 characters are truncated for analysis.
- If you edit the document after reviewing, run the review again so clause positions stay accurate.
- The backend has no authentication yet. Use synthetic or redacted agreements on a public demo.
- Findings are review prompts, not legal advice.
