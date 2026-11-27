/* Maatamudra Word add-in task pane.
 * Same-origin client for the FastAPI backend: /api/upload/analyze (review) and /api/addin/rewrite (suggest).
 * All dynamic text is inserted with textContent (never innerHTML). */
(function () {
  "use strict";

  const API = window.location.origin;
  const state = {
    inWord: false, lines: [], result: null, contractType: null, busy: false,
    contract: null, types: [], draftSpec: null, draftQuestions: [], draftContract: null, draftIsSample: false,
  };
  let started = false;

  const $ = (id) => document.getElementById(id);
  function el(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function setStatus(msg, isError) {
    ["status", "contractSetupStatus", "workspaceStatus"].forEach((id) => {
      const status = $(id);
      if (!status) return;
      status.textContent = msg || "";
      status.className = "status" + (isError ? " error" : "");
    });
  }
  function setBusy(b) {
    state.busy = b;
    $("btnReview").disabled = b;
  }

  // ---- API ---------------------------------------------------------------
  async function api(path, opts) {
    let res;
    try {
      res = await fetch(API + path, opts);
    } catch (e) {
      throw new Error("Cannot reach the Maatamudra server. Check your connection.");
    }
    if (!res.ok) {
      let detail = "";
      try { const j = await res.json(); detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail); } catch (_) {}
      if (res.status === 503) detail = detail || "The AI model is not configured on the server.";
      throw new Error(detail || ("Server error " + res.status));
    }
    return res.json();
  }
  const post = (path, body) => api(path, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  const postEmpty = (path) => api(path, { method: "POST" });
  const contractPath = (path) => "/api/contracts/" + encodeURIComponent(state.contract.id) + path;
  const outputCard = (title, value) => {
    const card = el("article", "output-card");
    if (title) card.append(el("h3", null, title));
    if (typeof value === "string") card.append(el("p", null, value));
    else {
      const pre = el("pre");
      pre.textContent = JSON.stringify(value, null, 2);
      card.append(pre);
    }
    return card;
  };
  const withAction = (button, label, action) => run(button, async () => {
    const original = button.textContent;
    button.textContent = label;
    try { await action(); } finally { button.textContent = original; }
  });

  // ---- reading the document ---------------------------------------------
  async function readWordLines() {
    return Word.run(async (ctx) => {
      const ps = ctx.document.body.paragraphs;
      ps.load("items/text");
      await ctx.sync();
      const lines = [];
      ps.items.forEach((p, i) => {
        const t = (p.text || "").replace(/\s+/g, " ").trim();
        if (t) lines.push({ i: i, t: t });   // i = real paragraph index in the document
      });
      return lines;
    });
  }
  function readPastedLines() {
    return $("paste").value.split(/\n+/).map((t, i) => ({ i: i, t: t.replace(/\s+/g, " ").trim() })).filter((l) => l.t);
  }

  // Map each analysed segment back to a range of document paragraphs by its heading (= first line, max 70 chars).
  function align(segments, lines) {
    let p = 0;
    segments.forEach((s) => { s.start = -1; s.end = -1; });
    for (const s of segments) {
      for (let k = p; k < lines.length; k++) {
        if (lines[k].t.slice(0, 70) === s.heading) { s.start = k; p = k + 1; break; }
      }
    }
    let next = lines.length;
    for (let j = segments.length - 1; j >= 0; j--) {
      if (segments[j].start >= 0) { segments[j].end = next - 1; next = segments[j].start; }
    }
  }

  async function segmentRange(ctx, seg) {
    if (seg.start < 0) throw new Error("This clause could not be located in the document. Run the review again.");
    const ps = ctx.document.body.paragraphs;
    ps.load("items/text");
    await ctx.sync();
    const first = ps.items[state.lines[seg.start].i];
    const last = ps.items[state.lines[seg.end].i];
    if (!first || !last || first.text.replace(/\s+/g, " ").trim().slice(0, 70) !== seg.heading) {
      throw new Error("The document has changed since the review. Run the review again.");
    }
    return first.getRange("Content").expandTo(last.getRange("Content"));
  }

  // ---- review ------------------------------------------------------------
  async function review() {
    if (state.busy) return;
    setBusy(true);
    $("results").hidden = true;
    try {
      setStatus("Reading the document…");
      state.lines = state.inWord ? await readWordLines() : readPastedLines();
      const text = state.lines.map((l) => l.t).join("\n\n");   // blank lines => paragraph-level segmentation
      if (text.length < 80) throw new Error("Not enough text to review. Open or paste an agreement first.");

      setStatus("Analysing clauses… this takes about 20–60 seconds.");
      const body = { text: text };
      if ($("ctype").value) body.contract_type = $("ctype").value;
      const result = await post("/api/upload/analyze", body);

      align(result.segments, state.lines);
      state.result = result;
      state.contract = null;
      state.draftContract = null;
      state.result.text = text;
      $("agreementTools").hidden = true;
      $("contractSetup").hidden = false;
      $("draftTools").hidden = true;
      state.contractType = result.contract_type;
      updateContractSetup();
      render(result, text.length > 60000);
      setStatus("");
    } catch (e) {
      setStatus(e.message, true);
    } finally {
      setBusy(false);
    }
  }

  // ---- rendering ---------------------------------------------------------
  function chip(label, value) {
    const c = el("span", "chip");
    c.append(label + " ");
    c.append(el("b", null, String(value)));
    return c;
  }

  function render(r, truncated) {
    const concerns = r.segments.filter((s) => s.concern);
    const gapsCore = (r.gaps && r.gaps.missing_basics) || [];
    const gapsOpt = (r.gaps && r.gaps.worth_considering) || [];
    const checks = r.checks || [];

    const sum = $("summary");
    sum.replaceChildren(
      chip("Type", r.type_title),
      chip("Clauses", r.segments.length),
      chip("Concerns", concerns.length),
      chip("Missing basics", gapsCore.length),
      chip("Term checks", checks.length)
    );
    if (r.extraction_method) sum.append(chip("Read via", r.extraction_method));
    if (truncated) sum.append(el("span", "warn", "Only the first ~60,000 characters were analysed."));

    // Concerns
    const box = $("concerns");
    box.replaceChildren();
    if (!concerns.length) box.append(el("p", "muted", "No clause-level concerns flagged. Still read the sections below."));
    concerns.forEach((s) => box.append(concernCard(s)));

    // Checks
    const cb = $("checks");
    cb.replaceChildren();
    if (checks.length) {
      checks.forEach((c) => {
        const d = el("div", "item sev-" + (c.severity || "warning"));
        d.append(el("div", "key", (c.severity || "warning").toUpperCase() + (c.clause_key ? " · " + c.clause_key : "")));
        d.append(el("p", null, c.message));
        cb.append(d);
      });
    } else if ((r.missing || []).length) {
      cb.append(el("p", "muted", "Checks need these terms, which the document does not clearly state:"));
      (r.questions || []).forEach((q) => cb.append(el("p", null, "• " + q.question)));
    } else {
      cb.append(el("p", "ok-note", "No contradictions found in the stated terms."));
    }

    // Gaps
    const gb = $("gaps");
    gb.replaceChildren();
    gapsCore.forEach((g) => gb.append(gapCard(g, true)));
    gapsOpt.forEach((g) => gb.append(gapCard(g, false)));
    if (!gapsCore.length && !gapsOpt.length) gb.append(el("p", "ok-note", "Every standard clause for this agreement type is present."));

    $("btnCommentAll").disabled = !(state.inWord && concerns.length);
    $("results").hidden = false;
  }

  function gapCard(g, core) {
    const d = el("div", "item " + (g.risk === "high" ? "high" : core ? "" : "low"));
    d.append(el("h3", null, g.title));
    d.append(el("div", "key", core ? "Missing basic clause" : "Worth considering"));
    d.append(el("p", null, g.why));
    return d;
  }

  function concernCard(seg) {
    const d = el("div", "item");
    d.append(el("h3", null, seg.heading));
    if (seg.clause_key) d.append(el("div", "key", "Matches clause: " + seg.clause_key));
    d.append(el("p", null, seg.concern));

    const instr = el("input");
    instr.type = "text";
    instr.placeholder = "Optional instruction, e.g. make the notice period mutual";
    instr.setAttribute("aria-label", "Optional rewrite instruction");

    const holder = el("div");
    const actions = el("div", "actions");
    const inWord = state.inWord && seg.start >= 0;

    const bFind = el("button", null, "Show in document");
    bFind.onclick = () => run(bFind, () => locate(seg));
    const bCom = el("button", null, "Add comment");
    bCom.onclick = () => run(bCom, () => comment(seg));
    const bRew = el("button", null, "Suggest balanced rewrite");
    bRew.onclick = () => run(bRew, () => suggest(seg, instr.value, holder));
    [bFind, bCom].forEach((b) => { b.disabled = !inWord; });
    actions.append(bFind, bCom, bRew);

    d.append(instr, actions, holder);
    return d;
  }

  async function run(btn, fn) {
    const old = btn.textContent;
    btn.disabled = true;
    try { setStatus(""); await fn(); } catch (e) { setStatus((old.trim() || "Action") + ": " + e.message, true); } finally {
      btn.disabled = btn.dataset.keepDisabled === "true";
      delete btn.dataset.keepDisabled;
      btn.textContent = old;
    }
  }

  // ---- document actions --------------------------------------------------
  async function locate(seg) {
    await Word.run(async (ctx) => { (await segmentRange(ctx, seg)).select(); await ctx.sync(); });
  }

  async function comment(seg) {
    await Word.run(async (ctx) => {
      const r = await segmentRange(ctx, seg);
      r.insertComment("Maatamudra: " + seg.concern + " (review prompt, not legal advice)");
      await ctx.sync();
    });
    setStatus("Comment added.");
  }

  async function commentAll() {
    const segs = state.result.segments.filter((s) => s.concern && s.start >= 0);
    let n = 0;
    await Word.run(async (ctx) => {
      const ps = ctx.document.body.paragraphs;
      ps.load("items/text");
      await ctx.sync();
      for (const s of segs) {
        const first = ps.items[state.lines[s.start].i];
        const last = ps.items[state.lines[s.end].i];
        if (!first || !last || first.text.replace(/\s+/g, " ").trim().slice(0, 70) !== s.heading) continue;
        first.getRange("Content").expandTo(last.getRange("Content"))
          .insertComment("Maatamudra: " + s.concern + " (review prompt, not legal advice)");
        n++;
      }
      await ctx.sync();
    });
    setStatus(n + " comment" + (n === 1 ? "" : "s") + " added.");
  }

  function updateContractSetup() {
        const missing = (state.result && state.result.missing) || [];
        $("extractedTerms").replaceChildren(
          outputCard("Extracted terms · verify names, amounts, dates and obligations", state.result && state.result.spec || {})
        );
        $("contractSetupNote").textContent = missing.length
          ? "Confirm the missing required terms before opening agreement-level tools: " + missing.join(", ") + "."
          : "Required details were extracted. Verify them first; selecting Create workspace & open tools saves this agreement to the demo workspace.";
        $("btnEnableTools").disabled = missing.length > 0;
      }

      async function clarifyTerms() {
        if (!state.result) throw new Error("Review an agreement first.");
        const message = $("clarification").value.trim();
        if (!message) throw new Error("Enter the agreed details or corrections first.");
        const response = await post("/api/intake", {
          message: message,
          spec: state.result.spec,
          previous_questions: state.result.questions || [],
        });
        state.result.spec = response.spec;
        state.result.missing = response.missing;
        state.result.questions = response.questions;
        $("clarification").value = "";
        updateContractSetup();
        if (response.missing.length) {
          $("contractSetupNote").textContent = "Still missing: " + response.missing.join(", ") + ". Add those agreed details and extract again.";
        } else {
          $("contractSetupNote").textContent = "Required details are now present. Review the extracted terms, then open the agreement tools.";
        }
        setStatus("Extracted terms updated. Verify every field before continuing.");
      }

      async function openAgreementTools() {
        if (!state.result || !state.result.spec) throw new Error("Review an agreement first.");
        if ((state.result.missing || []).length) throw new Error("Add the missing required terms before continuing.");
        const created = await post("/api/upload/contract", {
          spec: state.result.spec,
          segments: state.result.segments,
        });
        state.contract = created;
        state.contractType = created.spec.contract_type;
        state.draftContract = null;
        populateAgreementSelectors();
        $("agreementTools").hidden = false;
        $("draftTools").hidden = true;
        showToolPanel("legal");
        setStatus("Workspace created and tools are ready. Verify the saved terms before using results.");
      }

      function populateAgreementSelectors() {
        const clauseSelect = $("evidenceClause");
        clauseSelect.replaceChildren();
        (state.contract.clauses || []).forEach((clause) => {
          const option = el("option", null, clause.title || clause.key);
          option.value = clause.key;
          clauseSelect.append(option);
        });
        const type = state.types.find((item) => item.key === state.contract.spec.contract_type);
        const scenarios = (type && type.scenarios) || [];
        const select = $("scenarioSelect");
        select.replaceChildren();
        scenarios.forEach((scenario, index) => {
          const option = el("option", null, scenario.label || scenario.type);
          option.value = String(index);
          select.append(option);
        });
        renderScenarioInputs();
        const exports = $("contractExports");
        exports.replaceChildren();
        [
          ["Download DOCX", "/docx"],
          ["Download dates (.ics)", "/calendar.ics"],
          ["View obligations (JSON)", "/obligations"],
        ].forEach(([label, path]) => {
          const link = el("a", "button", label);
          link.href = API + contractPath(path);
          link.target = "_blank";
          link.rel = "noreferrer";
          exports.append(link);
        });
      }

      function showToolPanel(name) {
        document.querySelectorAll("#toolTabs button").forEach((button) => {
          button.setAttribute("aria-selected", String(button.dataset.panel === name));
        });
        document.querySelectorAll("#agreementTools .tool-panel").forEach((panel) => {
          panel.hidden = panel.id !== "panel-" + name;
        });
        $("draftTools").hidden = name !== "draft";
      }

      function renderScenarioInputs() {
        const target = $("scenarioInputs");
        target.replaceChildren();
        const type = state.types.find((item) => item.key === (state.contract && state.contract.spec.contract_type));
        const scenario = type && type.scenarios[Number($("scenarioSelect").value)];
        (scenario && scenario.inputs || []).forEach((field) => {
          const label = el("label", null, field.label || field.name);
          label.htmlFor = "scenario-" + field.name;
          const input = field.kind === "select" ? el("select") : el("input");
          input.id = "scenario-" + field.name;
          input.dataset.field = field.name;
          if (field.kind === "select") {
            (field.options || []).forEach((value) => {
              const option = el("option", null, value);
              option.value = value;
              input.append(option);
            });
          } else {
            input.type = field.kind === "range" ? "range" : (field.kind || "text");
            if (field.min != null) input.min = field.min;
            if (field.max != null) input.max = field.max;
          }
          if (field.default != null) input.value = field.default;
          target.append(label, input);
        });
      }

      function requireContract() {
        if (!state.contract || !state.contract.id) throw new Error("Open an agreement in the workspace first.");
        return contractPath("");
      }

      async function loadLegalContext() {
        requireContract();
        const [intelligence, statutes] = await Promise.all([
          api(contractPath("/legal-intelligence")),
          api(contractPath("/statutes")),
        ]);
        $("legalOutput").replaceChildren(
          outputCard("Legal intelligence · verify sources and applicability", intelligence),
          outputCard("Statutory references", statutes)
        );
      }

      async function loadEvidence() {
        requireContract();
        const key = $("evidenceClause").value;
        if (!key) throw new Error("Choose a clause first.");
        const evidence = await postEmpty(contractPath("/evidence/" + encodeURIComponent(key)));
        $("legalOutput").append(outputCard("Case-law evidence · source passages require human verification", evidence));
      }

      async function loadCopilotReview() {
        requireContract();
        const result = await postEmpty(contractPath("/copilot/review"));
        $("negotiationOutput").replaceChildren(outputCard("AI contract review", result));
      }

      function renderRedlines(contract) {
        const output = $("negotiationOutput");
        output.replaceChildren();
        const redlines = contract.redlines || [];
        if (!redlines.length) {
          output.append(el("p", "muted", "No negotiation redlines were returned."));
          return;
        }
        redlines.forEach((redline) => {
          const card = el("article", "output-card");
          card.append(el("h3", null, redline.clause_key + " · " + redline.status));
          card.append(el("p", null, "Current: " + redline.original));
          card.append(el("p", null, "Proposed: " + redline.proposed));
          card.append(el("p", null, redline.rationale || redline.legal_question || ""));
          if (redline.warning) card.append(el("p", "warn", redline.warning));
          const actions = el("div", "actions");
          const segment = (state.result && state.result.segments || []).find((item) => item.clause_key === redline.clause_key);
          const apply = el("button", null, "Apply in Word as tracked change");
          apply.disabled = !state.inWord || !segment || segment.start < 0 || redline.status !== "pending" || !!redline.warning;
          apply.onclick = () => run(apply, async () => {
            await applyRewrite(segment, redline.proposed);
            apply.dataset.keepDisabled = "true";
          });
          const reject = el("button", null, "Reject proposal");
          reject.disabled = redline.status !== "pending";
          reject.onclick = () => run(reject, async () => {
            const updated = await postEmpty(contractPath("/redlines/" + encodeURIComponent(redline.clause_key) + "/reject"));
            renderRedlines(updated);
          });
          actions.append(apply, reject);
          card.append(actions);
          if (!segment && state.inWord) card.append(el("p", "muted", "Run a fresh document review to map this clause before applying it."));
          output.append(card);
        });
      }

      async function runRedlineReview() {
        requireContract();
        const contract = await postEmpty(contractPath("/review"));
        renderRedlines(contract);
      }

      async function runPlaybookReview() {
        requireContract();
        const context = {
          side: $("reviewSide").value.trim() || "not specified",
          deadline: $("reviewDeadline").value.trim() || "not specified",
          deal_context: $("dealContext").value.trim(),
        };
        const result = await post(contractPath("/playbook-review"), context);
        $("negotiationOutput").replaceChildren(outputCard("Playbook review", result));
      }

      async function askAboutContract() {
        requireContract();
        const question = $("question").value.trim();
        if (!question) throw new Error("Enter a question about this agreement.");
        const result = await post(contractPath("/ask"), { question: question });
        $("answerOutput").replaceChildren(outputCard("Answer · check cited clauses", result));
      }

      async function explainContract() {
        requireContract();
        const result = await post(contractPath("/explain"), { language: $("explainLanguage").value });
        $("explainOutput").replaceChildren(outputCard("Plain-language explanation", result));
      }

      async function simulateScenario() {
        requireContract();
        const type = state.types.find((item) => item.key === state.contract.spec.contract_type);
        const scenario = type && type.scenarios[Number($("scenarioSelect").value)];
        if (!scenario) throw new Error("No what-if scenarios are available for this agreement type.");
        const payload = Object.assign({ type: scenario.type }, scenario.fixed || {});
        $("scenarioInputs").querySelectorAll("[data-field]").forEach((input) => {
          const raw = input.value;
          payload[input.dataset.field] = input.type === "number" || input.type === "range"
            ? Number(raw) : raw;
        });
        const result = await post(contractPath("/simulate"), payload);
        $("scenarioOutput").replaceChildren(outputCard(scenario.label || "What-if result", result));
      }

      async function loadObligations() {
        requireContract();
        const result = await api(contractPath("/obligations"));
        $("obligationsOutput").replaceChildren(outputCard("Obligations, dates and terms", result));
      }

      const executionStep = {
        stamp_duty: "stamp_duty_verified",
        registration: "registration_completed",
        signing: "signed_by_parties",
        lawyer: "legal_review_completed",
      };

      async function loadExecution() {
        requireContract();
        const result = await api(contractPath("/execution"));
        const output = $("executionOutput");
        output.replaceChildren();
        if (!result.supported) output.append(el("p", "warn", result.message));
        (result.items || []).forEach((item) => {
          const card = el("article", "output-card");
          card.append(el("h3", null, item.title + (item.done ? " · recorded" : "")));
          card.append(el("p", null, item.guidance));
          if (item.source_url) {
            const link = el("a", null, "Official source");
            link.href = item.source_url;
            link.target = "_blank";
            link.rel = "noreferrer";
            card.append(link);
          }
          const step = executionStep[item.id];
          if (step && !item.done) {
            const note = el("input");
            note.type = "text";
            note.placeholder = "Evidence note (date, receipt, or who confirmed)";
            const button = el("button", null, "Record completed step");
            button.onclick = () => run(button, async () => {
              if (note.value.trim().length < 5) throw new Error("Record at least five characters of evidence.");
              await post(contractPath("/execution/confirm"), { step: step, done: true, note: note.value.trim() });
              await loadExecution();
            });
            card.append(note, button);
          }
          output.append(card);
        });
      }

      async function loadConsequenceMap() {
        requireContract();
        const result = await api(contractPath("/consequence-map"));
        $("consequenceOutput").replaceChildren(outputCard("Consequence map · directional, not a legal determination", result));
      }

      function typeForDraft() {
        const key = $("draftType").value;
        const type = state.types.find((item) => item.key === key);
        if (!type) throw new Error("Choose a supported agreement type.");
        return type;
      }

      function loadDraftSample() {
        const type = typeForDraft();
        state.draftSpec = JSON.parse(JSON.stringify(type.sample));
        state.draftQuestions = [];
        state.draftIsSample = true;
        $("draftBrief").value = "";
        $("btnDraftCreate").disabled = false;
        $("draftQuestions").replaceChildren(outputCard("Synthetic example terms · edit or verify before creating", state.draftSpec));
        $("draftOutput").replaceChildren();
      }

      async function extractDraftTerms() {
        const type = typeForDraft();
        const message = $("draftBrief").value.trim();
        if (!message) throw new Error("Describe the agreed terms first.");
        const response = await post("/api/intake", {
          message: message,
          spec: state.draftSpec || { contract_type: type.key },
          previous_questions: state.draftQuestions,
        });
        state.draftSpec = response.spec;
        state.draftQuestions = response.questions || [];
        state.draftIsSample = false;
        $("btnDraftCreate").disabled = response.missing.length > 0;
        const content = [outputCard("Extracted terms · verify each detail", response.spec)];
        if (response.missing.length) {
          content.push(outputCard("Still needed", response.questions.map((question) => question.question)));
        } else {
          content.push(el("p", "ok-note", "Required terms are present. Verify names, numbers, dates and obligations before creating."));
        }
        $("draftQuestions").replaceChildren(...content);
      }

      async function createDraft() {
        const type = typeForDraft();
        if (!state.draftSpec) throw new Error("Load the synthetic example or extract details first.");
        if (state.draftSpec.contract_type !== type.key) throw new Error("The selected agreement type changed. Extract details again.");
        const created = await post("/api/contracts", state.draftSpec);
        state.draftContract = created;
        state.contract = created;
        state.contractType = type.key;
        state.result = null;
        populateAgreementSelectors();
        $("agreementTools").hidden = false;
        showToolPanel("draft");
        const output = $("draftOutput");
        output.replaceChildren(outputCard("Draft created · review before use", (created.clauses || []).map((clause) => ({
          title: clause.title, text: clause.text,
        }))));
        const insert = el("button", "primary", "Insert at cursor (after selection)");
        insert.disabled = !state.inWord;
        insert.onclick = () => run(insert, async () => {
          await insertDraftIntoWord();
          setStatus("Draft inserted. Review it carefully; nothing was signed or approved.");
        });
        const copy = el("button", null, "Copy agreement text");
        copy.onclick = () => run(copy, async () => {
          const text = (created.clauses || []).map((clause) => clause.title + "\n" + clause.text).join("\n\n");
          if (!navigator.clipboard) throw new Error("Clipboard access is unavailable in this browser.");
          await navigator.clipboard.writeText(text);
          setStatus("Agreement text copied.");
        });
        const actions = el("div", "actions");
        actions.append(insert, copy);
        const download = el("a", "button", "Download DOCX");
        download.href = API + contractPath("/docx");
        download.target = "_blank";
        download.rel = "noreferrer";
        actions.append(download);
        output.append(actions);
        setStatus("Draft created. Verify all terms and review with an Indian advocate.");
      }

      async function insertDraftIntoWord() {
        if (!state.inWord || !state.draftContract) throw new Error("Create a draft in Word first.");
        const text = "\n\n" + (state.draftContract.clauses || []).map((clause) => clause.title + "\n" + clause.text).join("\n\n") + "\n\n";
        await Word.run(async (ctx) => {
          ctx.document.getSelection().insertText(text, Word.InsertLocation.end);
          await ctx.sync();
        });
      }

  async function suggest(seg, instruction, holder) {
    holder.replaceChildren(el("p", "muted", "Drafting a balanced rewrite…"));
    const clauseText = state.lines.slice(seg.start >= 0 ? seg.start : 0, seg.end >= 0 ? seg.end + 1 : 1).map((l) => l.t).join("\n");
    const text = seg.start >= 0 ? clauseText : seg.text;
    try {
      const p = await post("/api/addin/rewrite", {
        clause_text: text.slice(0, 6000),
        contract_type: state.contractType,
        concern: seg.concern,
        instruction: instruction || null,
      });
      holder.replaceChildren(proposalView(seg, p));
    } catch (e) {
      holder.replaceChildren(el("p", "warn", e.message));
    }
  }

  function proposalView(seg, p) {
    const d = el("div", "proposal");
    d.append(el("div", "key", "Proposed replacement"));
    d.append(el("div", "text", p.proposed_text));
    d.append(el("p", null, p.rationale));
    (p.tradeoffs || []).forEach((t) => d.append(el("p", "muted", "Trade-off: " + t)));
    (p.warnings || []).forEach((w) => d.append(el("p", "warn", w)));
    d.append(el("p", "muted", p.disclaimer));

    const bar = el("div", "actions");
    const apply = el("button", "primary", "Apply as tracked change");
    apply.disabled = !(p.apply_allowed && state.inWord && seg.start >= 0);
    apply.onclick = () => run(apply, async () => {
      await applyRewrite(seg, p.proposed_text);
      apply.dataset.keepDisabled = "true";
    });
    const copy = el("button", null, "Copy text");
    copy.onclick = () => run(copy, async () => {
      if (!navigator.clipboard) throw new Error("Clipboard access is unavailable in this browser.");
      await navigator.clipboard.writeText(p.proposed_text);
      setStatus("Copied.");
    });
    bar.append(apply, copy);
    d.append(bar);
    return d;
  }

  async function applyRewrite(seg, newText) {
    await Word.run(async (ctx) => {
      const doc = ctx.document;
      doc.load("changeTrackingMode");
      await ctx.sync();
      const previous = doc.changeTrackingMode;
      doc.changeTrackingMode = Word.ChangeTrackingMode.trackAll;   // edits show as reviewable revisions
      await ctx.sync();
      try {
        const range = await segmentRange(ctx, seg);
        range.insertText(newText, Word.InsertLocation.replace);
        await ctx.sync();
      } finally {
        doc.changeTrackingMode = previous;
        await ctx.sync();
      }
    });
    setStatus("Applied as a tracked change. Review it in Word's Review tab (Accept / Reject).");
  }

  // ---- startup -----------------------------------------------------------
  async function loadTypes() {
    try {
      state.types = await api("/api/types");
      state.types.forEach((t) => {
        const o = el("option", null, t.title || t.key);
        o.value = t.key || t.contract_type;
        $("ctype").append(o);
        const draftOption = el("option", null, t.title || t.key);
        draftOption.value = t.key;
        $("draftType").append(draftOption);
      });
    } catch (e) {
      setStatus("Could not load agreement types: " + e.message, true);
    }
  }

  function init(host) {
    if (started) return;
    started = true;
    state.inWord = host === "Word" || (window.Office && Office.HostType && host === Office.HostType.Word);
    $("pasteBox").hidden = state.inWord;
    $("btnReview").onclick = review;
    $("btnShowDraft").onclick = () => {
      showToolPanel("draft");
      $("draftTools").scrollIntoView({ behavior: "smooth", block: "start" });
    };
    $("btnCommentAll").onclick = () => run($("btnCommentAll"), commentAll);
    $("btnClarify").onclick = () => withAction($("btnClarify"), "Updating…", clarifyTerms);
    $("btnEnableTools").onclick = () => withAction($("btnEnableTools"), "Opening…", openAgreementTools);
    $("btnDraftSample").onclick = () => run($("btnDraftSample"), loadDraftSample);
    $("btnDraftIntake").onclick = () => withAction($("btnDraftIntake"), "Extracting…", extractDraftTerms);
    $("btnDraftCreate").onclick = () => withAction($("btnDraftCreate"), "Creating…", createDraft);
    $("draftType").onchange = () => {
      state.draftSpec = null;
      state.draftQuestions = [];
      state.draftIsSample = false;
      $("btnDraftCreate").disabled = true;
      $("draftQuestions").replaceChildren();
      $("draftOutput").replaceChildren();
    };
    $("draftBrief").oninput = () => {
      if (!state.draftIsSample) return;
      state.draftSpec = null;
      state.draftIsSample = false;
      $("btnDraftCreate").disabled = true;
      $("draftQuestions").replaceChildren(el("p", "muted", "The synthetic sample was cleared. Extract your agreed details before creating a draft."));
    };
    $("scenarioSelect").onchange = renderScenarioInputs;
    document.querySelectorAll("#toolTabs button").forEach((button) => {
      button.onclick = () => showToolPanel(button.dataset.panel);
    });
    $("btnLegal").onclick = () => withAction($("btnLegal"), "Loading…", loadLegalContext);
    $("btnEvidence").onclick = () => withAction($("btnEvidence"), "Checking…", loadEvidence);
    $("btnCopilotReview").onclick = () => withAction($("btnCopilotReview"), "Reviewing…", loadCopilotReview);
    $("btnRedlineReview").onclick = () => withAction($("btnRedlineReview"), "Reviewing…", runRedlineReview);
    $("btnPlaybook").onclick = () => withAction($("btnPlaybook"), "Reviewing…", runPlaybookReview);
    $("btnAsk").onclick = () => withAction($("btnAsk"), "Asking…", askAboutContract);
    $("btnExplain").onclick = () => withAction($("btnExplain"), "Explaining…", explainContract);
    $("btnSimulate").onclick = () => withAction($("btnSimulate"), "Simulating…", simulateScenario);
    $("btnObligations").onclick = () => withAction($("btnObligations"), "Loading…", loadObligations);
    $("btnExecution").onclick = () => withAction($("btnExecution"), "Loading…", loadExecution);
    $("btnConsequenceMap").onclick = () => withAction($("btnConsequenceMap"), "Loading…", loadConsequenceMap);
    loadTypes();
  }

  if (window.Office && Office.onReady) {
    Office.onReady((info) => init(info && info.host));
    setTimeout(() => init(null), 3000);   // opened in a normal browser: Office.js never reports a host
  } else {
    init(null);
  }
})();
