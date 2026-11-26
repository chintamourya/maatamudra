/* Maatamudra Word add-in task pane.
 * Same-origin client for the FastAPI backend: /api/upload/analyze (review) and /api/addin/rewrite (suggest).
 * All dynamic text is inserted with textContent (never innerHTML). */
(function () {
  "use strict";

  const API = window.location.origin;
  const state = { inWord: false, lines: [], result: null, contractType: null, busy: false };
  let started = false;

  const $ = (id) => document.getElementById(id);
  function el(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function setStatus(msg, isError) {
    const s = $("status");
    s.textContent = msg || "";
    s.className = "status" + (isError ? " error" : "");
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
      state.contractType = result.contract_type;
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
    try { setStatus(""); await fn(); } catch (e) { setStatus(e.message, true); } finally { btn.disabled = false; btn.textContent = old; }
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
    apply.onclick = () => run(apply, async () => { await applyRewrite(seg, p.proposed_text); apply.disabled = true; });
    const copy = el("button", null, "Copy text");
    copy.onclick = () => navigator.clipboard && navigator.clipboard.writeText(p.proposed_text).then(() => setStatus("Copied."));
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
      const range = await segmentRange(ctx, seg);
      range.insertText(newText, Word.InsertLocation.replace);
      await ctx.sync();
      doc.changeTrackingMode = previous;
      await ctx.sync();
    });
    setStatus("Applied as a tracked change. Review it in Word's Review tab (Accept / Reject).");
  }

  // ---- startup -----------------------------------------------------------
  async function loadTypes() {
    try {
      const types = await api("/api/types");
      types.forEach((t) => {
        const o = el("option", null, t.title || t.key);
        o.value = t.key || t.contract_type;
        $("ctype").append(o);
      });
    } catch (_) { /* auto-detect still works */ }
  }

  function init(host) {
    if (started) return;
    started = true;
    state.inWord = host === "Word" || (window.Office && Office.HostType && host === Office.HostType.Word);
    $("pasteBox").hidden = state.inWord;
    $("btnReview").onclick = review;
    $("btnCommentAll").onclick = () => run($("btnCommentAll"), commentAll);
    loadTypes();
  }

  if (window.Office && Office.onReady) {
    Office.onReady((info) => init(info && info.host));
    setTimeout(() => init(null), 3000);   // opened in a normal browser: Office.js never reports a host
  } else {
    init(null);
  }
})();
