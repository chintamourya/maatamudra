# Maatamudra for Word

The Word task pane supports agreement review and drafting while keeping actions tied to the open document:

- Review clause concerns, stated-term checks, and missing clauses.
- Navigate to a concern, add a comment, or add comments for all flagged clauses.
- Request a balanced rewrite and apply it as a Word tracked change for accept/reject in Word.
- Clarify missing extracted terms, then open agreement tools for the reviewed document.
- Use legal intelligence, statutory references, clause-level case-law evidence, AI contract review,
  negotiation redlines, playbook review, questions, plain-language explanations, scenario simulations,
  obligations, execution checklist, consequence map, and DOCX/ICS/JSON exports.
- Draft a new agreement from an agreed brief or a clearly marked synthetic sample. Insert the generated text
  at the cursor after any selected text (without replacing that selection) or download a DOCX.

The tabs are scoped to the currently opened or created agreement. Market research and browser workspace
libraries remain in the full web workspace and are not represented as document-specific Word tools.

## Install (sideload) for the demo

The Maatamudra demo must be available over **HTTPS**. Ask the demo organizer for its URL, then:

**Word on the web**
1. Open `<demo-url>/addin/manifest.xml` and save the file as `manifest.xml`.
2. In Word on the web, open a document and choose **Home → Add-ins → More Settings → Upload My Add-in**
   (or **Insert → Add-ins**), then select the manifest file.
3. Use the Maatamudra button on the Home tab to open the task pane.

**Word desktop (Windows):** put `manifest.xml` in a folder, share the folder, add it under
*File → Options → Trust Center → Trusted Add-in Catalogs*, then *Insert → My Add-ins → Shared Folder*.

**Word desktop (Mac):** copy `manifest.xml` into
`~/Library/Containers/com.microsoft.Word/Data/Documents/wef`.

**Browser/paste mode:** open `<demo-url>/addin/taskpane.html` to review pasted agreement text and try drafting
and export flows. Word-only actions, including navigating and inserting text in the active document, require
Word.

## Reviewing an agreement

1. Open an agreement in Word and select **Review agreement**.
2. Inspect clause concerns, checks and missing clauses. **Show in document** navigates to a located clause;
   comments record findings in Word.
3. To rewrite text, choose **Suggest balanced rewrite**, inspect the proposal and warnings, then choose
   **Apply as tracked change**. Review and accept or reject the revision in Word's Review tab.
4. If required deal terms are missing, enter only facts the parties have agreed to and select
   **Update extracted terms**. Verify the extracted terms before selecting **Create workspace & open tools**;
   that explicit action saves a workspace record in the demo backend.
5. Use the agreement tabs for legal references and evidence, negotiation/playbook reviews, Ask/Explain,
   what-if scenarios, obligations, execution steps and exports.
6. If the document changes, run the review again before applying clause-specific suggestions.

## Drafting an agreement

1. Select **Draft a new agreement** and choose a supported agreement type.
2. Either load the explicitly synthetic example or describe the agreed terms and select **Extract details**.
3. Check every extracted name, amount, date and obligation. Resolve missing required fields using agreed facts.
4. Select **Create agreement** only after verifying the details.
5. In Word, choose **Insert at cursor (after selection)** to add the generated text without replacing
   selected text, or download the DOCX. Review the resulting agreement independently before use.

## Limits and safety

- Findings and AI-generated text are prompts, not legal advice or lawyer certification. Legal references,
  case-law evidence, simulations and execution guidance need source and fact verification.
- Rewrites can be applied only when the add-in can map the reviewed clause to the open Word document.
  Re-run the review after document edits; unmapped clauses cannot be applied automatically.
- The Word add-in reads document paragraphs. Scanned/image-only documents are not supported in Word.
- Reviews are limited to approximately 60,000 characters.
- The demo has no authentication or document access controls. Use synthetic or redacted agreements only.
- Generated text is not signed, approved, stamped or registered. Arrange appropriate independent legal review
  and execution outside the demo.

## Quick demo

1. Open a sample agreement in Word and click **Review agreement**.
2. Inspect a concern with **Show in document**, then add a comment.
3. Request a balanced rewrite and apply it as a tracked change; demonstrate Word's accept/reject controls.
4. Try **Law & evidence** or **Ask & explain** after opening agreement tools.
5. Choose **Draft a new agreement**, load the synthetic example, create it, and insert it at the cursor.
