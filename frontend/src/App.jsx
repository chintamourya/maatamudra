import React, { useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import { wordDiff } from "./diff.js";
import { LANGS, canListen, listen, speak } from "./voice.js";

const Chip = ({ v }) => <span className={`chip ${v}`}>{String(v).replace("_", " ")}</span>;
const HEADLINES = {
  late_fee: "Late fee under the contract", late_interest: "Late interest under the contract",
  lock_in_rent_liability: "Lock-in rent liability", refund_amount: "Deposit refund", renewal_rent: "Renewal rent",
  net_payable_to_freelancer: "Net payable to freelancer", kill_fee: "Kill fee", salary_for_notice_period: "Salary for notice period",
  claimable_under_contract: "Bond named in the contract", owner: "Owner of the work",
};
const PROV = { inferred: "worked out", suggested_default: "suggested", document: "from document" };
const money = (k, v) => (k === "owner" ? v : `₹${Number(v).toLocaleString("en-IN")}`);
const makeDraftId = () => globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`;
const DEMO_STORAGE_KEY = "maatamudra:browser-identity:v1";
const getBrowserIdentity = () => {
  let id = window.localStorage.getItem(DEMO_STORAGE_KEY);
  if (!id) {
    id = makeDraftId();
    window.localStorage.setItem(DEMO_STORAGE_KEY, id);
  }
  return id;
};
const BROWSER_ID = typeof window === "undefined" ? "server" : getBrowserIdentity();
const DRAFTS_KEY = `maatamudra:drafts:v1:${BROWSER_ID}`;
const ACTIVE_DRAFT_KEY = `maatamudra:active-draft:v1:${BROWSER_ID}`;
const PERSONA_KEY = `maatamudra:persona:v1:${BROWSER_ID}`;
const hasSavedDraftContent = (draft) => Boolean(
  draft?.contractId ||
  draft?.message?.trim() ||
  draft?.questions?.length ||
  Object.entries(draft?.spec || {}).some(([key, value]) =>
    key !== "contract_type" && key !== "provenance" && value !== null && value !== ""),
);
const TYPE_PRESENTATION = {
  rental_agreement: ["⌂", "Home & tenancy"],
  freelance_service: ["↗", "Freelance, consulting & services"],
  employment: ["◌", "Hiring & employment"],
  nda: ["◇", "Protect confidential information"],
  sale_purchase: ["▣", "Buy or sell goods"],
  partnership: ["♧", "Start or run a partnership"],
  private_loan: ["₹", "Simple private bilateral loans"],
  ip_licence: ["©", "Software, content & intellectual property"],
  mou: ["≋", "Explore a collaboration"],
};
const INDIA_STATES = [
  "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat",
  "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh",
  "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
  "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh",
  "Uttarakhand", "West Bengal", "Andaman and Nicobar Islands", "Chandigarh",
  "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Jammu and Kashmir", "Ladakh",
  "Lakshadweep", "Puducherry",
];

export default function App() {
  const [types, setTypes] = useState([]);
  const [persona, setPersona] = useState("citizen");
  const [drafts, setDrafts] = useState([]);
  const draftsRef = useRef([]);
  const draftMessageRef = useRef(null);
  const [activeDraftId, setActiveDraftId] = useState(null);
  const [draftsReady, setDraftsReady] = useState(false);
  const [topView, setTopView] = useState("workspace");
  const [contracts, setContracts] = useState([]);
  const [detailsOpen, setDetailsOpen] = useState(true);
  const [checksOpen, setChecksOpen] = useState(true);
  const [mobilePanel, setMobilePanel] = useState("details");
  const [typeQuery, setTypeQuery] = useState("");
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState("");
  const [typeKey, setTypeKey] = useState("rental_agreement");
  const [spec, setSpec] = useState({ contract_type: "rental_agreement", provenance: {} });
  const [msg, setMsg] = useState("");
  const [questions, setQuestions] = useState([]);
  const [contract, setContract] = useState(null);
  const [sel, setSel] = useState(null);
  const [tab, setTab] = useState("evidence");
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");
  const [mode, setMode] = useState("draft");
  const [analysis, setAnalysis] = useState(null);
  const [paste, setPaste] = useState("");
  const [fname, setFname] = useState("");
  const [fileB64, setFileB64] = useState("");
  const [listening, setListening] = useState(false);
  const [vlang, setVlang] = useState("en-IN");
  const [demoIdentity, setDemoIdentity] = useState(null);
  const [demoIdentityBusy, setDemoIdentityBusy] = useState(false);
  const [marketOpen, setMarketOpen] = useState(false);
  const [marketData, setMarketData] = useState(null);
  const [marketLoading, setMarketLoading] = useState(false);
  const [marketError, setMarketError] = useState("");
  const [guideOpen, setGuideOpen] = useState(false);
  const [guideSection, setGuideSection] = useState("start");

  useEffect(() => {
    api.types().then(setTypes).catch((e) => setErr(e.message));
    api.health().then(setHealth).catch((e) => setHealthError(e.message));
    api.listContracts().then(setContracts).catch(() => setContracts([]));
  }, []);
  useEffect(() => {
    let active = true;
    const restore = async () => {
      try {
        const storedDrafts = JSON.parse(window.localStorage.getItem(DRAFTS_KEY) || "[]");
        if (!Array.isArray(storedDrafts)) throw new Error("Saved drafts are in an unreadable format.");
        const availableDrafts = storedDrafts.filter((draft) =>
          draft && typeof draft.id === "string" && hasSavedDraftContent(draft));
        draftsRef.current = availableDrafts;
        setDrafts(availableDrafts);
        const savedPersona = window.localStorage.getItem(PERSONA_KEY);
        if (["citizen", "advocate", "business"].includes(savedPersona)) setPersona(savedPersona);
        const selectedId = window.localStorage.getItem(ACTIVE_DRAFT_KEY);
        const selectedDraft = availableDrafts.find((draft) => draft.id === selectedId);
        if (selectedDraft) {
          setActiveDraftId(selectedDraft.id);
          setPersona(selectedDraft.persona || savedPersona || "citizen");
          setTypeKey(selectedDraft.typeKey || "rental_agreement");
          setSpec(selectedDraft.spec || { contract_type: selectedDraft.typeKey || "rental_agreement", provenance: {} });
          setMsg(selectedDraft.message || "");
          setQuestions(selectedDraft.questions || []);
          setMode(selectedDraft.mode || "draft");
          if (selectedDraft.contractId) {
            try {
              const savedContract = await api.get(selectedDraft.contractId);
              if (active) {
                setContract(savedContract);
                setSel(savedContract.clauses[0]?.key);
                setTab("copilot");
                setMobilePanel("main");
              }
            } catch (e) {
              if (active) setErr(`Could not reopen the saved agreement: ${e.message}`);
            }
          }
        } else {
          setActiveDraftId(makeDraftId());
        }
      } catch (e) {
        if (active) {
          setErr(`Could not load saved drafts: ${e.message}`);
          setActiveDraftId(makeDraftId());
        }
      } finally {
        if (active) setDraftsReady(true);
      }
    };
    restore();
    return () => { active = false; };
  }, []);
  useEffect(() => {
    if (!draftsReady || !activeDraftId) return;
    const existingDraft = draftsRef.current.find((draft) => draft.id === activeDraftId);
    if (!hasSavedDraftContent({
      contractId: contract?.id || existingDraft?.contractId,
      message: msg,
      questions,
      spec,
    })) return;
    try {
      const type = types.find((item) => item.key === typeKey);
      const party = spec.landlord_name || spec.tenant_name || spec.employer_name || spec.employee_name ||
        spec.client_name || spec.freelancer_name || spec.party_a || spec.party_b;
      const saved = {
        id: activeDraftId,
        title: `${type?.title || typeKey}${party ? ` · ${party}` : ""}`,
        typeKey,
        persona,
        spec,
        message: msg,
        questions,
        mode,
        contractId: contract?.id || existingDraft?.contractId || null,
        updatedAt: new Date().toISOString(),
      };
      const nextDrafts = [saved, ...draftsRef.current.filter((draft) => draft.id !== activeDraftId)].slice(0, 30);
      window.localStorage.setItem(DRAFTS_KEY, JSON.stringify(nextDrafts));
      window.localStorage.setItem(ACTIVE_DRAFT_KEY, activeDraftId);
      window.localStorage.setItem(PERSONA_KEY, persona);
      draftsRef.current = nextDrafts;
      setDrafts(nextDrafts);
    } catch (e) {
      setErr(`Could not save this draft on this device: ${e.message}`);
    }
  }, [draftsReady, activeDraftId, persona, typeKey, spec, msg, questions, mode, contract, types]);
  const td = types.find((t) => t.key === typeKey);
  const demoAvailable = types.some((type) => type.key === "freelance_service" && type.sample);
  const visibleTypes = types.filter((type) => {
    const [_, subtitle] = TYPE_PRESENTATION[type.key] || ["", ""];
    return `${type.title} ${subtitle}`.toLowerCase().includes(typeQuery.trim().toLowerCase());
  });

  const run = async (label, fn) => {
    setBusy(label); setErr("");
    try { return await fn(); } catch (e) { setErr(e.message); } finally { setBusy(""); }
  };
  const showMobilePanel = (panel) => {
    if (window.matchMedia("(max-width: 640px)").matches) {
      setDetailsOpen(true);
      setChecksOpen(true);
    }
    setMobilePanel(panel);
  };
  const hasDraftContent = () => Boolean(contract || analysis || msg.trim() || questions.length ||
    Object.entries(spec).some(([key, value]) =>
      key !== "contract_type" && key !== "provenance" && value !== null && value !== ""));
  const pickType = (key) => {
    if (hasDraftContent()) setActiveDraftId(makeDraftId());
    setTypeKey(key); setSpec({ contract_type: key, provenance: {} }); setQuestions([]); setContract(null); setSel(null); setTab("evidence");
  };
  const sendIntake = () => run("intake", async () => {
    const r = await api.intake(msg, spec, questions); setSpec(r.spec); setQuestions(r.questions); setMsg("");
  });
  const create = () => run("create", async () => {
    const c = await api.create(spec);
    setContract(c); setSel(c.clauses[0]?.key); setTab("copilot"); showMobilePanel("main");
    api.listContracts().then(setContracts).catch(() => {});
  });
  const clause = contract?.clauses.find((c) => c.key === sel);
  const reset = (forceNewDraft = false) => {
    if (forceNewDraft || hasDraftContent()) setActiveDraftId(makeDraftId());
    setContract(null); setAnalysis(null); setSel(null); setQuestions([]); setMsg("");
    setSpec({ contract_type: typeKey, provenance: {} }); setPaste(""); setFname(""); setFileB64("");
  };
  const switchMode = (m) => { reset(); setMode(m); setErr(""); };
  const startNewDraft = () => {
    setMode("draft");
    reset(true);
    setErr("");
    showMobilePanel("details");
    revealDraftEditor();
  };
  const loadFreelanceDemo = () => {
    const demoType = types.find((type) => type.key === "freelance_service");
    if (!demoType?.sample) {
      setErr("The synthetic freelancer sample is unavailable.");
      return;
    }
    setActiveDraftId(makeDraftId());
    setMode("draft");
    setAnalysis(null);
    setContract(null);
    setSel(null);
    setTypeKey(demoType.key);
    setTypeQuery("");
    setSpec(demoType.sample);
    setQuestions([]);
    setMsg("");
    setErr("");
    showMobilePanel("details");
    revealDraftEditor();
  };
  const revealDraftEditor = () => {
    window.requestAnimationFrame(() => {
      draftMessageRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  };
  const openDraft = (draft) => {
    setActiveDraftId(draft.id);
    setPersona(draft.persona || "citizen");
    setTypeKey(draft.typeKey || "rental_agreement");
    setSpec(draft.spec || { contract_type: draft.typeKey || "rental_agreement", provenance: {} });
    setMsg(draft.message || "");
    setQuestions(draft.questions || []);
    setMode(draft.mode || "draft");
    setAnalysis(null);
    setPaste("");
    setFname("");
    setFileB64("");
    setContract(null);
    setSel(null);
    setErr("");
    showMobilePanel("details");
    revealDraftEditor();
    if (draft.contractId) run("restore", async () => {
      const savedContract = await api.get(draft.contractId);
      setContract(savedContract);
      setSel(savedContract.clauses[0]?.key);
      setTab("copilot");
      showMobilePanel("main");
    });
  };
  const openContract = async (contractSummary) => {
    await run("restore", async () => {
      const savedContract = await api.get(contractSummary.id);
      setContract(savedContract);
      setSel(savedContract.clauses[0]?.key);
      setTypeKey(savedContract.spec.contract_type);
      setSpec(savedContract.spec);
      setTab("copilot");
      setTopView("workspace");
      showMobilePanel("main");
    });
  };
  const pickFile = (f) => {
    if (!f) return;
    setFname(f.name);
    const r = new FileReader();
    r.onload = () => setFileB64(String(r.result).split(",")[1] || "");
    r.readAsDataURL(f);
  };
  const analyze = () => run("analyze", async () => {
    const a = await api.uploadAnalyze(fileB64 ? { filename: fname, content_b64: fileB64 } : { text: paste });
    setAnalysis(a); setSpec(a.spec); setTypeKey(a.contract_type); setQuestions(a.questions);
    showMobilePanel("main");
  });
  const refine = () => run("intake", async () => {
    const r = await api.intake(msg, spec, questions); setSpec(r.spec); setQuestions(r.questions); setMsg("");
    setAnalysis((a) => ({ ...a, spec: r.spec, missing: r.missing, questions: r.questions }));
  });
  const openUpload = () => run("create", async () => {
    const c = await api.uploadOpen({ spec, segments: analysis.segments, filename: fname || "pasted text" });
    setContract(c); setSel(c.clauses[0]?.key); setTab("copilot"); showMobilePanel("main");
    api.listContracts().then(setContracts).catch(() => {});
  });
  const dictate = () => {
    if (listening) return;
    setListening(true);
    listen(vlang, (t) => setMsg((m) => (m ? m + " " : "") + t), () => setListening(false));
  };
  const openMarketResearch = async () => {
    setMarketOpen(true);
    if (marketData) return;
    setMarketLoading(true); setMarketError("");
    try { setMarketData(await api.marketResearch()); }
    catch (e) { setMarketError(e.message); }
    finally { setMarketLoading(false); }
  };
  const refreshMarketResearch = async () => {
    setMarketLoading(true); setMarketError("");
    try { setMarketData(await api.marketResearch()); }
    catch (e) { setMarketError(e.message); }
    finally { setMarketLoading(false); }
  };
  const updateState = (value) => {
    setSpec((current) => {
      const provenance = { ...current.provenance };
      if (value) provenance.state = "user";
      else delete provenance.state;
      return { ...current, state: value || null, provenance };
    });
    if (value) setQuestions((current) => current.filter((question) => question.field !== "state"));
  };

  const missingBasics = analysis?.gaps?.missing_basics || [];
  return (
    <div className={`app${detailsOpen ? "" : " details-collapsed"}${checksOpen ? "" : " checks-collapsed"} mobile-panel-${mobilePanel}`}>
      <header className="top">
        <div className="brand" aria-label="Maatamudra, మాటముద్ర"><span className="brand-mark">మ</span><span><b>Maatamudra</b><small>AGREEMENTS · COMMITMENTS · CLARITY</small></span></div>
        <div className="top-status" aria-live="polite">
          <span className={`status-dot ${health?.llm_configured ? "ready" : health ? "attention" : ""}`} />
          {healthError ? "Connection unavailable" : health?.llm_configured ? "AI workspace ready" : health ? "AI setup needed" : "Connecting"}
        </div>
        <span className="sp" />
        <nav className="top-workspace-tabs" role="tablist" aria-label="Workspace tools">
          <button role="tab" aria-selected={topView === "workspace"} className={topView === "workspace" ? "active" : ""} onClick={() => setTopView("workspace")}>Workspace</button>
          <button role="tab" aria-selected={topView === "drafts"} className={topView === "drafts" ? "active" : ""} onClick={() => { setTopView("drafts"); showMobilePanel("details"); }}>Drafts</button>
          <button role="tab" aria-selected={topView === "contracts"} className={topView === "contracts" ? "active" : ""} onClick={() => { setTopView("contracts"); showMobilePanel("details"); api.listContracts().then(setContracts).catch((e) => setErr(e.message)); }}>Contracts</button>
          <button role="tab" onClick={openMarketResearch}>Market</button>
          <button role="tab" onClick={() => { setGuideSection("start"); setGuideOpen(true); }}>Guide</button>
          <button role="tab" onClick={() => { setGuideSection("word"); setGuideOpen(true); }}>Word add-in</button>
        </nav>
        <div className="persona-switch top-persona" aria-label="Workspace mode">
          {[ ["citizen", "Citizen"], ["advocate", "Advocate"], ["business", "Business"] ].map(([key, label]) =>
            <button key={key} className={persona === key ? "on" : ""} onClick={() => setPersona(key)}>{label}</button>)}
        </div>
        {contract && <>
          <a className="top-link" href={api.docxUrl(contract.id)}>Export .docx</a>
          <a className="top-link optional-link" href={api.icsUrl(contract.id)}>Calendar</a>
          <a className="top-link optional-link" href={api.jsonUrl(contract.id)} target="_blank" rel="noreferrer">Terms JSON</a>
        </>}
      </header>
      <nav className="mobile-nav" role="tablist" aria-label="Workspace sections">
        {[["details", "Draft"], ["main", "Agreement"], ["checks", "Guidance"]].map(([panel, label]) => (
          <button key={panel} role="tab" aria-selected={mobilePanel === panel} onClick={() => showMobilePanel(panel)}>{label}</button>
        ))}
      </nav>
      {demoIdentity && <IdentitySimulation result={demoIdentity} onClose={() => setDemoIdentity(null)} />}
      {guideOpen && <UserGuide initialSection={guideSection} onClose={() => setGuideOpen(false)} />}
      {marketOpen && <MarketResearchDashboard data={marketData} loading={marketLoading} error={marketError} onClose={() => setMarketOpen(false)} onRefresh={refreshMarketResearch} />}

      <section className={`pane pane-details${detailsOpen ? "" : " pane-hidden"}`} aria-label="Details">
        <div className="pane-title-row"><div className="section-kicker"><span className="kicker-line" /> YOUR AGREEMENT</div><button className="pane-close" onClick={() => setDetailsOpen(false)} aria-label="Hide details panel" title="Hide details panel">−</button></div>
        {topView === "drafts" && <div className="draft-history library-view">
          <div className="draft-history-heading"><b>Saved drafts</b><button onClick={startNewDraft}>New draft +</button></div>
          <p>Private to this browser profile; not shared with other browser profiles. Uploaded files aren’t saved. Real account isolation is not enabled in this demo.</p>
          <div className="draft-history-list">
            {drafts.map((draft) => (
              <button key={draft.id} className={`draft-history-item${draft.id === activeDraftId ? " active" : ""}`} aria-current={draft.id === activeDraftId ? "true" : undefined} onClick={() => openDraft(draft)}>
                <span>{draft.title || "Untitled draft"}</span><small>{draft.id === activeDraftId ? "Editing" : draft.contractId ? "Generated agreement" : "In progress"} · {new Date(draft.updatedAt).toLocaleString()}</small>
              </button>
            ))}
            {drafts.length === 0 && <span className="draft-history-empty">Your drafts will appear here as you work.</span>}
          </div>
        </div>}
        {topView === "contracts" && <div className="draft-history library-view">
          <div className="draft-history-heading"><b>Generated contracts</b><button onClick={() => { setTopView("workspace"); startNewDraft(); }}>New contract +</button></div>
          <p>Contracts generated in this workspace are shown here. A production user-account boundary is required for true cross-user privacy.</p>
          <div className="draft-history-list">
            {contracts.map((item) => (
              <button key={item.id} className="draft-history-item" onClick={() => openContract(item)}>
                <span>{item.title || item.type}</span><small>{item.type} · {new Date(item.updated_at).toLocaleString()}</small>
              </button>
            ))}
            {contracts.length === 0 && <span className="draft-history-empty">No generated contracts yet.</span>}
          </div>
        </div>}
        {topView === "workspace" && <>
        <div className="modes" role="tablist" aria-label="Mode">
          <button role="tab" aria-selected={mode === "draft"} onClick={() => switchMode("draft")}><span>✳</span> Create new</button>
          <button role="tab" aria-selected={mode === "upload"} onClick={() => switchMode("upload")}><span>↗</span> Review a document</button>
        </div>

        {mode === "upload" && !analysis && (
          <>
            <h2>Start with what<br />you already have.</h2>
            <p className="muted">We’ll map the clauses, surface gaps and help you see what deserves a closer look.</p>
            <label className="upload-zone">
              <span className="upload-icon">↑</span><strong>{fname || "Choose an agreement"}</strong>
              <span className="muted">Word, searchable or scanned PDF, or .txt · OCR for scanned PDFs (English; Hindi/Telugu if installed)</span>
              <input type="file" accept=".docx,.pdf,.txt" onChange={(e) => pickFile(e.target.files[0])} aria-label="Agreement file" />
            </label>
            <textarea rows={6} value={paste} onChange={(e) => { setPaste(e.target.value); setFileB64(""); setFname(""); }} placeholder="…or paste the agreement text here" />
            <div className="row"><button className="primary" disabled={busy || (!fileB64 && paste.trim().length < 80)} onClick={analyze}>{busy === "analyze" ? "Reading the agreement…" : "Check this agreement"}</button></div>
          </>
        )}

        {(mode === "draft" || analysis) && (
          <>
            {mode === "draft" && (<>
              <div className="section-kicker"><span className="kicker-line" /> {persona.toUpperCase()} WORKSPACE</div>
              <h2>{persona === "advocate" ? <>Draft, review and<br />negotiate with context.</> : persona === "business" ? <>Make business<br />agreements clearer.</> : <>Let’s make the<br />important parts clear.</>}</h2>
              <p className="muted">{persona === "advocate" ? "Use structured drafting, legal evidence, clause-level risk checks and two-sided redlines." : persona === "business" ? "Create service, vendor and commercial agreements, then review obligations and execution steps." : "Describe the arrangement in your own words. Maatamudra turns your instructions into editable terms and explains what deserves attention."}</p>
              <input className="type-search" type="search" value={typeQuery} onChange={(e) => setTypeQuery(e.target.value)} placeholder="Find an agreement type" aria-label="Find an agreement type" />
              <div className="typepick" role="radiogroup" aria-label="Agreement type">
                {visibleTypes.map((t) => (
                  <button key={t.key} role="radio" aria-checked={t.key === typeKey} className={t.key === typeKey ? "on" : ""} onClick={() => pickType(t.key)}>
                    <span className="type-icon">{TYPE_PRESENTATION[t.key]?.[0] || "↗"}</span><span>{t.title}<small>{TYPE_PRESENTATION[t.key]?.[1] || "Agreement template"}</small></span><span className="type-arrow">↗</span>
                  </button>
                ))}
              </div>
              {visibleTypes.length === 0 && <p className="field-hint">No agreement types match “{typeQuery}”. Try a broader search.</p>}
            </>)}
            {mode === "upload" && analysis && !contract && <h3>Terms found in your agreement</h3>}
            {!contract && (<>
              <label className="field-label" htmlFor="agreement-state">State / Union Territory</label>
              <select id="agreement-state" value={spec.state || ""} onChange={(e) => updateState(e.target.value)}>
                <option value="">Choose where this agreement is based</option>
                {INDIA_STATES.map((state) => <option key={state} value={state}>{state}</option>)}
              </select>
              <p className="field-hint">Select the State or Union Territory relevant to your agreement. Central-law issue spotting is available; local amendments, stamp duty and registration rules need current verification. Maatamudra never invents a duty amount.</p>
              <textarea ref={draftMessageRef} rows={mode === "upload" ? 3 : 5} value={msg} onChange={(e) => setMsg(e.target.value)}
                placeholder={mode === "upload" ? "Add or correct a detail, e.g. the notice period is 30 days" : "Describe the arrangement in your language. For example: I am renting my 2BHK flat in Hyderabad for ₹22,000 a month for 11 months with a two-month deposit."} />
              <div className="row">
                <button className="primary" disabled={!msg || busy} onClick={mode === "upload" ? refine : sendIntake}>{busy === "intake" ? "Reading…" : "Add details"}</button>
                <select value={vlang} onChange={(e) => setVlang(e.target.value)} aria-label="Speaking language" style={{ width: "auto" }}>{LANGS.map(([c, l]) => <option key={c} value={c}>{l}</option>)}</select>
                <button onClick={dictate} disabled={!canListen || listening} title={canListen ? "Speak your details" : "Speech input is not available in this browser"} aria-label="Speak">{listening ? "Listening…" : "🎤"}</button>
              </div>
              {mode === "draft" && <div className="row"><button className="quiet-button" onClick={() => { td && setSpec(td.sample); setQuestions([]); }}>Try a sample agreement <span>↗</span></button></div>}
            </>)}
            {questions.length > 0 && <div className="card"><b>Still needed</b>{questions.map((q) => <p key={q.field}>{q.question}</p>)}</div>}
            <h3 className="subheading">Your details <span>{td ? `${Object.keys(td.labels).filter((k) => spec[k] != null).length} added` : ""}</span></h3>
            {td && Object.entries(td.labels).filter(([k]) => spec[k] != null).map(([k, l]) => (
              <div className="field" key={k}><span>{l}</span>
                <span>{String(spec[k])} <i>{PROV[spec.provenance?.[k]] || ""}</i></span></div>
            ))}
            {mode === "upload" && analysis && <p className="muted">Check these against your document. The time machine uses them.</p>}
            {!contract && <div className="row"><button className="primary create-button" disabled={busy || !td || td.required.some((f) => spec[f] == null)} onClick={mode === "upload" ? openUpload : create}>
              {busy === "create" ? "Working…" : mode === "upload" ? "Open full review" : "Draft agreement"}</button></div>}
            {!contract && td && td.required.some((f) => spec[f] == null) && <p className="field-hint">Still needed: {td.required.filter((f) => spec[f] == null).map((f) => td.labels[f] || f).join(", ")}</p>}
            {(analysis || contract) && <div className="row"><button onClick={reset}>Start over</button></div>}
          </>
        )}
        </>}
      </section>

      <main className="pane pane-main" aria-label="Agreement">
        <div className="workspace-controls">
          {!detailsOpen && <button onClick={() => setDetailsOpen(true)}>Show details</button>}
          {!checksOpen && <button onClick={() => setChecksOpen(true)}>Show checks</button>}
        </div>
        {err && <div className="err global-error" role="alert">{err}</div>}
        {contract ? (
          <div className="doc">
            <div className="document-heading"><div><div className="section-kicker"><span className="kicker-line" /> THE AGREEMENT</div><h2>{td?.title}</h2></div><span className="chip pending">{contract.source?.uploaded ? "Your document · under review" : "Draft · not signed"}</span></div>
            <div className="document-meta"><span>⌖ {contract.spec.state || "State not specified"}</span><span>·</span><span>{contract.clauses.length} clauses</span><span>·</span><span>Terms from your brief</span></div>
            {contract.clauses.map((c, i) => (
              <button key={c.key} className={`clause r-${c.risk} ${sel === c.key ? "sel" : ""}`} onClick={() => setSel(c.key)}>
                <h4><span className="clause-number">{String(i + 1).padStart(2, "0")}</span>{c.title}{c.risk !== "low" && <Chip v={c.risk} />}{c.status === "revised" && <Chip v="revised" />}</h4>
                {c.text}
              </button>
            ))}
          </div>
        ) : mode === "upload" && analysis ? (
          <div className="doc">
            <h3>{analysis.type_title}: what we found</h3>
            {analysis.checks.length > 0 && <>
              <h4 className="sub">Flags on the terms</h4>
              {analysis.checks.map((f, i) => <div className="card" key={i}><Chip v={f.severity === "error" ? "high" : f.severity} /> {f.message}</div>)}
            </>}
            {(missingBasics.length > 0 || analysis.gaps.worth_considering.length > 0) && <>
              <h4 className="sub">Missing from your agreement</h4>
              {missingBasics.map((g) => <div className="card" key={g.clause_key}><b>{g.title}</b> <Chip v="medium" /><p>{g.why}</p></div>)}
              {analysis.gaps.worth_considering.map((g) => <div className="card" key={g.clause_key}><b>{g.title}</b> <span className="muted">worth considering</span><p>{g.why}</p></div>)}
            </>}
            <h4 className="sub">Your clauses</h4>
            {analysis.segments.map((sg) => (
              <div className="clause" key={sg.idx} style={{ cursor: "default" }}>
                <h4>{sg.clause_key ? sg.clause_key.replace(/_/g, " ") : "unrecognised"}{sg.concern && <span className="chip medium">{sg.concern}</span>}</h4>
                {sg.text}
              </div>
            ))}
          </div>
        ) : <div className="welcome-story">
          <div className="story-glow" aria-hidden="true" />
          <div className="story-copy">
            <div className="section-kicker"><span className="kicker-line" /> A CALMER WAY TO AGREE</div>
            <h1>Good agreements<br />start with <em>clarity.</em></h1>
            <p>Turn the details you already know into a draft you can understand, question and review—one step at a time.</p>
            <div className="story-rule" />
            <div className="story-steps">
              {[["01", "Describe", "Start in your own words"], ["02", "Understand", "See each term clearly"], ["03", "Pressure-test", "Explore what could happen"], ["04", "Decide", "Review evidence, together"]].map(([n, title, copy], i) => (
                <div className="story-step" key={n}><span className="story-step-no">{n}</span><span className="story-step-copy"><b>{title}</b><small>{copy}</small></span>{i < 3 && <span className="step-connector" aria-hidden="true" />}</div>
              ))}
            </div>
            <div className="story-demo">
              <button className="primary create-button" disabled={!demoAvailable} onClick={loadFreelanceDemo}>
                {demoAvailable ? "Try a synthetic freelancer agreement" : "Preparing the synthetic demo…"}
              </button>
              <p className="field-hint">Loads sample details only; review them before generating the draft.</p>
            </div>
          </div>
          <div className="story-note"><span>✳</span><p><b>Built for careful decisions.</b><br />No invented terms. No “legally valid” badge. Just a clearer way to review.</p></div>
        </div>}
      </main>

      <aside className={`pane pane-checks${checksOpen ? "" : " pane-hidden"}`} aria-label="Checks">
        <div className="pane-title-row"><div className="section-kicker"><span className="kicker-line" /> CHECKS &amp; GUIDANCE</div><button className="pane-close" onClick={() => setChecksOpen(false)} aria-label="Hide checks panel" title="Hide checks panel">−</button></div>
        {!contract ? <div className="aside-welcome">
          <div className="section-kicker"><span className="kicker-line" /> BUILT FOR TRUST</div>
          <h3>Nothing happens behind your back.</h3>
          <p>Every suggestion is a starting point for your decision—not a substitute for one.</p>
          <div className="trust-list">
            <div><span>01</span><p><b>Your terms stay yours</b><small>Optional terms are never silently invented.</small></p></div>
            <div><span>02</span><p><b>Evidence stays checkable</b><small>Sources and verification status are shown.</small></p></div>
            <div><span>03</span><p><b>You stay in control</b><small>Review, accept or reject proposed changes.</small></p></div>
          </div>
          <div className="source-note"><b>Case-law source</b><span>{health?.case_law_source === "indiankanoon" ? "Indian Kanoon API" : health?.case_law_source === "tavily" ? "Indian Kanoon pages · web search" : health?.case_law_source === "none" ? "Not configured" : healthError ? "Unavailable" : "Checking availability"}</span></div>
          <p className="legal-note"><span>ⓘ</span> Open-source Indian contract intelligence. State/UT-specific rules are shown with coverage and verification status; unverified rules are never presented as settled.</p>
        </div> : (
          <>
            <div className="copilot-heading"><div className="copilot-orb">✳</div><div><h3>Agreement guide</h3><span>{health?.llm_configured ? "AI-assisted · grounded in your terms" : "Set up AI to enable assisted review"}</span></div></div>
            <div className="source-note">
              <b>Evidence source</b>
              <span>{health?.case_law_source === "indiankanoon" ? "Indian Kanoon API" : health?.case_law_source === "tavily" ? "Web search · Indian Kanoon pages" : health?.case_law_source === "none" ? "Not configured" : "Checking availability"}</span>
            </div>
            <div className="tabs" role="tablist">
              {[["copilot", "AI Studio"], ["evidence", "Evidence"], ["legal", "India law"], ["review", "Negotiate & review"], ["time", "Time machine"], ["ask", "Ask"], ["explain", "Explain"], ["exec", "Execution"]].map(([k, l]) => (
                <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}>{l}</button>
              ))}
            </div>
            {tab === "copilot" && <CopilotStudio {...{ contract, clause, setContract, run, busy, health, setSel }} />}
            {tab === "evidence" && <Evidence {...{ contract, clause, setContract, run, busy, setErr }} />}
            {tab === "legal" && <LegalContext contract={contract} />}
            {tab === "review" && <Review {...{ contract, clause, setContract, run, busy, setSel, td, setErr }} />}
            {tab === "time" && <TimeMachine {...{ contract, run, busy, td, setErr }} />}
            {tab === "ask" && <Ask {...{ contract, run, busy, setSel }} />}
            {tab === "explain" && <Explain {...{ contract, run, busy }} />}
            {tab === "exec" && <Execution {...{ contract, setContract, run, setErr }} />}
            <p className="legal-note"><span>ⓘ</span> Assistive draft, not legal advice. Confirm state rules and legal conclusions with a qualified lawyer.</p>
          </>
        )}
      </aside>
    </div>
  );
}

function CopilotStudio({ contract, clause, setContract, run, busy, health, setSel }) {
  const [scan, setScan] = useState(null);
  const [proposal, setProposal] = useState(null);
  const [termChange, setTermChange] = useState(null);
  const [targetKey, setTargetKey] = useState(clause?.key || contract.clauses[0]?.key || "");
  const [instruction, setInstruction] = useState("");
  const aiAvailable = Boolean(health?.llm_configured);

  useEffect(() => {
    setScan(null);
    setProposal(null);
    setTermChange(null);
    setInstruction("");
    setTargetKey(contract.clauses[0]?.key || "");
  }, [contract.id]);
  useEffect(() => { setScan(null); }, [contract.updated_at]);
  useEffect(() => {
    if (clause?.key) setTargetKey(clause.key);
  }, [clause?.key]);

  const review = () => run("copilot-review", async () => {
    setScan(await api.copilotReview(contract.id));
  });
  const proposeRewrite = () => run("copilot-rewrite", async () => {
    const result = await api.copilotRewrite(contract.id, targetKey, instruction);
    if (result.intent === "term_change") {
      setTermChange(result.term_change);
      setProposal(null);
    } else {
      setProposal(result);
      setTermChange(null);
    }
    setContract(await api.get(contract.id));
  });
  const applyRewrite = () => run("copilot-apply", async () => {
    setContract(await api.copilotApply(contract.id, proposal.suggestion_id));
    setSel(targetKey);
    setProposal(null);
    setScan(null);
  });
  const dismissRewrite = () => run("copilot-dismiss", async () => {
    setContract(await api.copilotDismiss(contract.id, proposal.suggestion_id));
    setProposal(null);
  });
  const applyTermChange = () => run("copilot-term-apply", async () => {
    const updated = await api.copilotApplyTerm(contract.id, termChange.suggestion_id);
    setContract(updated);
    setSel(updated.clauses.some((item) => item.key === targetKey) ? targetKey : updated.clauses[0]?.key);
    setTermChange(null);
    setScan(null);
    setProposal(null);
  });
  const dismissTermChange = () => run("copilot-term-dismiss", async () => {
    if (termChange.suggestion_id) setContract(await api.copilotDismissTerm(contract.id, termChange.suggestion_id));
    setTermChange(null);
  });
  const riskClass = (priority) => priority === "high" ? "high" : priority === "medium" ? "medium" : "low";

  return (
    <div className="copilot-studio">
      <div className="copilot-intro">
        <div className="copilot-orb">✳</div>
        <div><h3>AI Contract Studio</h3><p>Review the whole agreement, then refine a clause with an approval step.</p></div>
      </div>
      {!aiAvailable && <div className="card copilot-setup"><b>AI is not configured</b><p>Configure the model connection to run the contract scan and clause drafting. The rest of your agreement tools remain available.</p></div>}

      <section className="copilot-section">
        <div className="copilot-section-head">
          <div><span className="copilot-step">01 · REVIEW</span><h4>Find what deserves attention</h4></div>
          <button className="primary" disabled={!aiAvailable || !!busy} onClick={review}>
            {busy === "copilot-review" ? "Reviewing agreement…" : scan ? "Run scan again" : "Scan agreement"}
          </button>
        </div>
        <p className="muted">Checks clause clarity, contradictions, missing details, one-sided terms, and practical gaps against the terms you provided.</p>
        {scan && <>
          <div className="copilot-summary">
            <Chip v={scan.overall_attention} />
            <p>{scan.summary}</p>
          </div>
          {scan.findings.length === 0 && <p className="muted">No review prompts were returned. This is not a legal-validity check.</p>}
          {scan.findings.map((finding, i) => (
            <article className="copilot-finding" key={`${finding.title}-${i}`}>
              <div className="copilot-finding-title"><span className="copilot-index">{String(i + 1).padStart(2, "0")}</span><b>{finding.title}</b><Chip v={riskClass(finding.priority)} /></div>
              <p>{finding.observation}</p>
              <p><b>Why it matters:</b> {finding.impact}</p>
              <p><b>Suggested next step:</b> {finding.next_step}</p>
              {finding.clause_keys.length > 0 && <div className="copilot-citations"><span>Related clauses</span>{finding.clause_keys.map((key) => {
                const cited = contract.clauses.find((item) => item.key === key);
                return cited ? <button key={key} onClick={() => setSel(key)}>{cited.title} ↗</button> : null;
              })}</div>}
              {!finding.numbers_match_source && <p className="copilot-warning">Verify figures in this finding: {finding.unmatched_numbers.join(", ")}</p>}
            </article>
          ))}
          {scan.open_questions.length > 0 && <details className="card copilot-questions"><summary>Questions to resolve ({scan.open_questions.length})</summary><ul>{scan.open_questions.map((question, i) => <li key={i}>{question}</li>)}</ul></details>}
          {scan.warnings.map((warning, i) => <p className="copilot-warning" key={i}>{warning}</p>)}
          <details className="card copilot-trace">
            <summary>What the AI checked</summary>
            <p>Reviewed {scan.basis.clauses_reviewed.length} clauses and {scan.basis.deterministic_checks_included} deterministic checks. No external legal sources were used for this scan.</p>
            <div className="copilot-citations"><span>Agreement clauses</span>{scan.basis.clauses_reviewed.map((key) => {
              const checked = contract.clauses.find((item) => item.key === key);
              return checked ? <button key={key} onClick={() => setSel(key)}>{checked.title} ↗</button> : null;
            })}</div>
            <p className="field-hint">This is an evidence-scope summary, not the model’s private reasoning. For legal sources, use Evidence and India law.</p>
          </details>
          {!scan.number_integrity && <p className="copilot-warning">Some figures were not found in the agreement or structural checks. Verify all amounts, dates, and periods manually.</p>}
        </>}
      </section>

      <section className="copilot-section">
        <div className="copilot-section-head"><div><span className="copilot-step">02 · CO-DRAFT</span><h4>Improve one clause</h4></div></div>
        <p className="muted">Ask for clearer wording or a specific change. The AI sees this agreement’s terms and related clauses.</p>
        <label className="field-label" htmlFor="copilot-clause">Clause to improve</label>
        <select id="copilot-clause" value={targetKey} disabled={Boolean(proposal || termChange)} onChange={(e) => { setTargetKey(e.target.value); setProposal(null); setTermChange(null); }}>
          {contract.clauses.map((item) => <option key={item.key} value={item.key}>{item.title}</option>)}
        </select>
        <label className="field-label" htmlFor="copilot-instruction">What should be clearer or different?</label>
        <textarea id="copilot-instruction" rows={3} maxLength={1200} value={instruction} disabled={Boolean(proposal || termChange)} onChange={(e) => { setInstruction(e.target.value); setProposal(null); setTermChange(null); }} placeholder="For example: change the notice period from 60 days to 75 days." />
        <div className="row"><button className="primary" disabled={!aiAvailable || !!busy || instruction.trim().length < 8} onClick={proposeRewrite}>
          {busy === "copilot-rewrite" ? "Drafting alternatives…" : "Draft a clause improvement"}
        </button></div>
        {termChange && <>
          <div className="copilot-term-change">
            <div className="copilot-finding-title"><b>Agreement term change · {termChange.label}</b><Chip v={termChange.can_apply ? "medium" : "high"} /></div>
            <p className="copilot-term-values"><span>Current</span><b>{String(termChange.current_value ?? "Not set")}</b><span>Requested</span><b>{String(termChange.requested_value)}</b></p>
            <p>{termChange.rationale}</p>
            {termChange.validation_error && <p className="copilot-warning">{termChange.validation_error}</p>}
            {termChange.can_apply && <>
              <p className="copilot-regenerate-note"><b>Review before continuing.</b> Applying this updates the agreed term to {String(termChange.requested_value)} and regenerates the whole draft. Clause rewrites, evidence, redlines, and execution checklist confirmations will be cleared. Use this only before signing.</p>
              <div className="row"><button className="primary" disabled={!!busy} onClick={applyTermChange}>{busy === "copilot-term-apply" ? "Updating agreement…" : "Update term & regenerate agreement"}</button></div>
            </>}
            <button disabled={!!busy} onClick={dismissTermChange}>{busy === "copilot-term-dismiss" ? "Discarding…" : "Keep current term"}</button>
          </div>
        </>}
        {proposal && <>
          <div className="copilot-proposal">
            <div className="copilot-finding-title"><b>Proposed wording · {proposal.clause_title}</b><Chip v={proposal.number_integrity ? "verified" : "high"} /></div>
            <p><b>Why it changed:</b> {proposal.rationale}</p>
            {proposal.tradeoffs.map((tradeoff, i) => <p className="muted" key={i}>Trade-off: {tradeoff}</p>)}
            <details><summary>Compare current and proposed wording</summary>
              <div className="copilot-diff">{wordDiff(proposal.original_text, proposal.proposed_text).map((part, i) => <span key={i} className={part.t}>{part.w} </span>)}</div>
            </details>
            {!proposal.number_integrity && <p className="copilot-warning">This proposal changes numeric terms, so it cannot be applied. Update the agreed facts first and request a new draft.</p>}
            {proposal.apply_allowed && <p className="field-hint">Applying replaces this exact clause text. Review it carefully; you can still inspect or revise the agreement afterward.</p>}
            <div className="row">
              {proposal.apply_allowed && <button className="primary" disabled={!!busy} onClick={applyRewrite}>{busy === "copilot-apply" ? "Applying…" : "Use this exact rewrite"}</button>}
              <button disabled={!!busy} onClick={dismissRewrite}>{busy === "copilot-dismiss" ? "Discarding…" : "Discard proposal"}</button>
            </div>
          </div>
        </>}
      </section>
      <p className="legal-note"><span>ⓘ</span>AI suggestions are drafts, not legal advice. Check every clause and get qualified Indian legal review before signing. State-specific rules are not verified by the AI scan.</p>
    </div>
  );
}


function IdentitySimulation({ result, onClose }) {
  return (
    <div className="guide-backdrop" role="dialog" aria-modal="true" aria-label="Demo identity simulation">
      <section className="guide-panel identity-panel">
        <div className="guide-head"><div><span className="section-kicker">HACKATHON DEMONSTRATION</span><h2>Demo identity flow</h2><p className="muted">A simulated sign-in and role-selection response.</p></div><button className="guide-close" onClick={onClose} aria-label="Close">×</button></div>
        <div className="identity-result"><span className="identity-mark">✓</span><div><b>Simulation response received</b><p>{result.notice || "This is a demonstration only."}</p></div></div>
        <dl className="identity-fields"><div><dt>Demo status</dt><dd>{result.status || "simulated"}</dd></div><div><dt>Selected workspace role</dt><dd>{result.role || "Not returned"}</dd></div><div><dt>Identity verification</dt><dd>Not performed</dd></div><div><dt>Access-control enforcement</dt><dd>Not performed</dd></div></dl>
        <p className="guide-warning">This button does not create an account, verify a person, authenticate a session, or protect documents. Do not upload confidential or personal documents to this public demo.</p>
        <div className="guide-actions"><button className="guide-primary" onClick={onClose}>Return to Maatamudra</button></div>
      </section>
    </div>
  );
}

function UserGuide({ initialSection, onClose }) {
  const [section, setSection] = useState(initialSection);
  const sections = [
    ["start", "Start here"], ["create", "Create an agreement"], ["review", "Review a document"],
    ["workspace", "Understand the workspace"], ["personas", "Citizen / Advocate / Business"],
    ["execution", "Execution & exports"], ["word", "Use in Word"], ["demo", "Demo features & safety"],
  ];
  const content = {
    start: <><h3>End-to-end journey</h3><ol className="guide-list"><li><b>Use the top tabs.</b> Workspace is for drafting or reviewing; Drafts lists meaningful drafts saved in this browser profile; Contracts lists generated agreements from the demo backend; Word add-in opens the Word setup instructions.</li><li><b>Choose a task.</b> In Workspace, select <em>Create new</em> to draft from a brief, or <em>Review a document</em> to inspect an existing agreement.</li><li><b>Select an agreement type and jurisdiction.</b> Pick the closest template and the relevant Indian State/UT.</li><li><b>Describe the deal in plain language.</b> Include parties, scope, payment, dates, deliverables, termination, deposit and other agreed terms. Do not assume missing terms.</li><li><b>Resolve follow-up questions.</b> Review extracted fields and add only facts the parties have actually agreed to.</li><li><b>Draft and review.</b> When required details are complete, choose <em>Draft agreement</em>. Inspect every clause and use the right-hand tabs to check evidence, legal context and proposed changes.</li><li><b>Export and complete execution outside this demo.</b> Download the DOCX, inspect the final version with the parties/lawyer, and arrange appropriate stamping, signing and registration independently.</li></ol><div className="guide-callout"><b>Try it end to end:</b> load the synthetic freelancer sample in Workspace, choose <b>Draft agreement</b>, inspect the payment and termination clauses, export the DOCX, then switch to <b>Review a document</b> and upload that file. Drafts are saved locally after meaningful details are entered, not just by opening the workspace. Drafts are browser-profile-specific; generated contracts do not have real account access controls in this demo.</div></>,
    create: <><h3>Create a new agreement</h3><ol className="guide-list"><li>Choose the <b>Workspace</b> top tab and make sure <b>Create new</b> is selected.</li><li>Choose one of the nine starters: rental, freelance/service, employment, NDA, sale/purchase, partnership, private loan, IP licence or MOU. Use the search field if needed.</li><li>Choose the State/UT that governs the transaction. If unsure, pause and seek advice rather than selecting a state arbitrarily.</li><li>Enter the facts in the plain-language box and select <b>Add details</b>. Include parties, scope, payments, dates, deliverables, warranties, confidentiality, IP ownership, termination and dispute handling where relevant.</li><li>Read the follow-up questions and add missing facts using <b>Add details</b> again. Do not invent details to clear a required field.</li><li>When the required fields are complete, select <b>Draft agreement</b>. The agreement appears in the centre pane; select a clause to inspect it and use the right pane for evidence and review tools.</li></ol><div className="guide-callout"><b>Example (fictional):</b> choose Rental agreement and Telangana, then enter: “I’m Priya, renting a 2BHK at 12 Sample Road, Hyderabad from Asha Rao for 11 months starting 1 January 2027. Rent is ₹22,000 per month, the deposit is ₹44,000, rent is due on the 5th, and notice is 30 days.” Confirm the extracted fields and answer follow-up questions with the agreed facts.</div><p>Meaningful draft details are autosaved in this browser profile and appear under <b>Drafts</b>. Empty drafts are not saved. Verify all names, amounts, dates, schedules and annexures.</p></>,
    review: <><h3>Review an existing agreement</h3><ol className="guide-list"><li>In <b>Workspace</b>, choose <b>Review a document</b>.</li><li>Upload a supported PDF, DOCX or TXT file, or paste at least 80 characters of agreement text.</li><li>Select <b>Check this agreement</b>. Scanned PDFs may use OCR; compare extracted names, amounts, dates, tables, stamps and signatures against every original page.</li><li>Read the agreement type, clause segments, risk flags, missing basics and items worth considering in the centre pane.</li><li>Add corrections or context in the left pane and select <b>Add details</b>. When required terms are complete, choose <b>Open full review</b>.</li><li>Inspect clauses and evidence. Treat flagged issues as prompts for review, not legal conclusions. Uploaded source files are not saved with drafts.</li></ol><p>Never upload Aadhaar, PAN, bank details, medical information, confidential client files or unredacted live contracts to the public demo.</p></>,
    workspace: <><h3>Right-hand agreement tools</h3><ul className="guide-feature-list"><li><b>AI Studio:</b> scan for ambiguity, contradictions, missing details and practical gaps; inspect the clauses and deterministic checks included. Ask for a clause rewrite, compare the proposed wording and apply it only after review. When you request a different supported deal fact, such as a notice period, AI proposes a validated term update; applying it regenerates the whole draft and clears derived review state. Wording-only rewrites cannot silently change numbers. The scan does not use external legal sources.</li><li><b>Evidence:</b> inspect clause-level support, source material and verification status. A citation must be checked for relevance and current validity.</li><li><b>India law:</b> view central-law context and State/UT coverage notes. Coverage is not a complete state-law opinion; stamp duty, registration, tenancy and employment rules need current local verification.</li><li><b>Negotiate & review:</b> run the two-sided review, then run the playbook-based review after entering your side, deadline, focus areas and deal context. Inspect GREEN/YELLOW/RED findings, business impact, negotiation priorities and fallback redlines. For NDA agreements, run the separate NDA pre-screen. Explicitly accept or reject redlines only after checking the full clause in context.</li><li><b>Time machine:</b> change scenario inputs to see how the agreement's own terms may affect outcomes. It is an illustrative calculation, not a prediction or legal ruling.</li><li><b>Ask:</b> ask questions about the current agreement. Check the answer against the clause text and cited material.</li><li><b>Explain:</b> request a plain-language explanation in a supported Indian language. Translation is machine-generated and is not certified legal translation.</li><li><b>Execution:</b> review extracted obligations and checklist items; mark only steps you have actually completed. Signing hand-off is simulated in this build.</li></ul></>,
    personas: <><h3>Three workspace perspectives</h3><div className="guide-role"><b>Citizen</b><p>Understand a personal agreement, create a first draft from agreed facts, review a document and identify questions to take to a lawyer.</p></div><div className="guide-role"><b>Advocate</b><p>Use the drafting and document-review studio as an assistive starting point; inspect legal sources, clauses, risks and proposed redlines. Independently verify authorities and provide professional review.</p></div><div className="guide-role"><b>Business</b><p>Prepare repeatable commercial agreement drafts, review supplier/customer terms, examine obligations and use the execution checklist to coordinate next steps.</p></div><p>The role switch is a UI persona selector only. It does not create separate accounts, permissions, workspaces or document isolation.</p></>,
    execution: <><h3>Exports and execution checklist</h3><ul className="guide-feature-list"><li><b>Export .docx:</b> download the editable agreement draft for final review.</li><li><b>Calendar:</b> export dated obligations/reminders where available and import them into a calendar tool.</li><li><b>Terms JSON:</b> inspect structured obligation data for downstream workflows.</li><li><b>Execution checklist:</b> use the checklist to track practical steps such as review, stamping, signing and registration. A checked box is only a user-recorded status.</li><li><b>Signing simulation:</b> demonstrates a provider hand-off shape only. It does not apply a legally recognised electronic signature or call a live CCA-licensed provider.</li></ul><div className="guide-callout">Before signing: verify party identity, authority to sign, final version, stamp duty, witness/notary requirements where applicable, registration requirements and execution formalities for the specific transaction and State/UT.</div></>,
    word: <><h3>Review an agreement in Microsoft Word</h3><ol className="guide-list"><li><b>Install the add-in.</b> Use the Word on the web flow: open the manifest below and save it as <em>manifest.xml</em>. In Word, open a document and choose <b>Home → Add-ins → More Settings → Upload My Add-in</b> (or <b>Insert → Add-ins</b>), then select the saved manifest. A <b>Review agreement</b> button appears on the Home tab.</li><li><b>Run a review.</b> Open an agreement in Word and choose <b>Review agreement</b>. Wait for the analysis to finish.</li><li><b>Inspect a finding.</b> Select a concern, then choose <b>Show in document</b> to jump to the relevant text. Add comments to record issues.</li><li><b>Apply a rewrite only after review.</b> Choose <b>Suggest balanced rewrite</b>, inspect the suggested wording, then choose <b>Apply as tracked change</b>. Use Word's Review tab to accept or reject it.</li><li><b>Re-run after editing.</b> If you change the document, run the review again so the findings match the current text.</li></ol><div className="guide-callout"><b>Example:</b> open the synthetic DOCX you exported from Workspace, select <b>Review agreement</b>, inspect a finding with <b>Show in document</b>, then compare a suggested rewrite before applying it as a tracked change.<br /><br /><b>Open this demo's Word add-in manifest</b><p>Word add-ins require an HTTPS demo. Download or save the manifest, then upload it from Word on the web.</p><a href="/addin/manifest.xml" target="_blank" rel="noreferrer">Open manifest.xml ↗</a></div><p className="guide-warning">The add-in sends document text to Maatamudra for review. It has no sign-in or document access controls in this demo. Use synthetic or redacted agreements only. Scanned/image-only documents are not supported in Word; findings are prompts, not legal advice.</p></>,
    demo: <><h3>Demo integrations and limitations</h3><ul className="guide-feature-list"><li><b>Demo identity flow:</b> returns a simulated identity/role result only; no real authentication or authorisation.</li><li><b>Signing-provider hand-off:</b> simulated only; no real eSign, Aadhaar eKYC, DSC validation or signature certificate.</li><li><b>Translation:</b> LLM-based translation across supported Scheduled Indian Languages; not a certified translation.</li><li><b>OCR:</b> Tesseract/PyMuPDF extraction is fallible; manually verify all extracted content.</li><li><b>Market viability:</b> open the <b>Market</b> top tab for curated research, editable scenarios, revenue assumptions, competitors and validation sprints. Forecasts are hypotheses, not actual traction or guaranteed revenue.</li><li><b>Word add-in:</b> use the <b>Word add-in</b> top tab for installation and review instructions.</li></ul><p className="guide-warning">Maatamudra is a hackathon prototype, not a lawyer, law firm, government portal, e-stamp service or production-secure document vault. Do not treat a generated draft as legally valid without independent review.</p></>,
  };
  return (
    <div className="guide-backdrop" role="dialog" aria-modal="true" aria-label="Maatamudra end-to-end user guide">
      <section className="guide-panel">
        <div className="guide-head"><div><span className="section-kicker">MAATAMUDRA · PRODUCT GUIDE</span><h2>{section === "word" ? "Use Maatamudra in Word" : "How to use Maatamudra"}</h2><p className="muted">{section === "word" ? "Install the add-in, review an agreement and apply changes as tracked revisions." : "A guided walkthrough from first input to reviewed draft and next steps."}</p></div><button className="guide-close" onClick={onClose} aria-label="Close guide">×</button></div>
        <div className="guide-body"><nav className="guide-nav" aria-label="Guide chapters">{sections.map(([key,label],i)=><button key={key} className={section===key?"active":""} onClick={()=>setSection(key)}><span>{String(i+1).padStart(2,"0")}</span>{label}</button>)}</nav><article className="guide-content">{content[section]}</article></div>
        <div className="guide-footer"><span>Use synthetic data in the public demo. Verify legal details independently.</span><div><button onClick={()=>setSection(sections[Math.max(0,sections.findIndex(x=>x[0]===section)-1)][0])} disabled={section==="start"}>Previous</button><button className="guide-primary" onClick={()=> section=== "demo" ? onClose() : setSection(sections[Math.min(sections.length-1,sections.findIndex(x=>x[0]===section)+1)][0])}>{section==="demo"?"Finish":"Next chapter →"}</button></div></div>
      </section>
    </div>
  );
}

function MarketResearchDashboard({ data, loading, error, onClose, onRefresh }) {
  const [scenario, setScenario] = useState("base");
  const [monthlyPrice, setMonthlyPrice] = useState(1299);
  const [iteration, setIteration] = useState(0);
  const [completed, setCompleted] = useState([]);
  const [tab, setTab] = useState("overview");
  const fmt = (n) => `₹${Math.round(n).toLocaleString("en-IN")}`;
  const compact = (n) => n >= 10000000 ? `₹${(n / 10000000).toFixed(2)} Cr` : n >= 100000 ? `₹${(n / 100000).toFixed(1)} L` : fmt(n);
  if (!data) return <div className="market-backdrop"><section className="market-panel"><div className="market-head"><div><span className="section-kicker">MAATAMUDRA · BUSINESS CASE</span><h2>Startup viability & market research</h2></div><button onClick={onClose}>Close</button></div>{loading ? <p>Loading dated research and assumptions…</p> : <div className="err">{error || "Market research is unavailable."}</div>}<button onClick={onRefresh}>Retry</button></section></div>;
  const model = data.model;
  const plan = model.scenarios[scenario];
  const reachable = 56100000 * (model.serviceable_share_pct / 100) * (model.reachable_share_of_serviceable_pct / 100);
  const rows = plan.years.map((y, i) => {
    const prior = i === 0 ? 0 : plan.years[i - 1].paying_customers;
    const avgPaid = (prior + y.paying_customers) / 2;
    const annualRevenue = avgPaid * monthlyPrice * 12;
    return { ...y, annualRevenue, arr: y.paying_customers * monthlyPrice * 12, conversion: y.paying_customers / Math.max(1, y.registered_users) * 100 };
  });
  const current = data.research_iterations[iteration % data.research_iterations.length];
  return (
    <div className="market-backdrop" role="dialog" aria-modal="true" aria-label="Startup viability and market research">
      <section className="market-panel">
        <div className="market-head">
          <div><span className="section-kicker">MAATAMUDRA · BUSINESS CASE · {data.research_as_of}</span><h2>Startup viability & market research</h2><p className="muted">India-first contract intelligence · bottom-up planning model</p></div>
          <div className="market-head-actions"><button onClick={onRefresh} disabled={loading}>{loading ? "Refreshing…" : "Refresh snapshot"}</button><button className="market-close" onClick={onClose} aria-label="Close market research">×</button></div>
        </div>
        <div className="market-tabs" role="tablist">
          {[["overview","Market & gaps"],["economics","User & revenue model"],["competition","Competitive map"],["iterations","Research iterations"]].map(([k,l]) => <button key={k} role="tab" aria-selected={tab===k} onClick={() => setTab(k)}>{l}</button>)}
        </div>
        {tab === "overview" && <>
          <div className="market-kpis">
            {data.market_context.slice(0,4).map((m) => <div className="market-kpi" key={m.label}><span>{m.label}</span><b>{m.value}</b><small>{m.detail}</small></div>)}
          </div>
          <h3>Where Maatamudra can win</h3>
          <div className="market-gap-grid">{data.gaps.map((g,i) => <article className="market-card" key={g.gap}><span className="market-index">0{i+1}</span><h4>{g.gap}</h4><p><b>Current gap</b><br/>{g.current_state}</p><p><b>Maatamudra approach</b><br/>{g.vachan_play}</p><small><b>Validation:</b> {g.validation}</small></article>)}</div>
          <h3>Target segments and recommended sequence</h3>
          <div className="market-segments">{data.segments.map((s) => <article key={s.name}><div><b>{s.name}</b><span className={`market-priority ${s.priority.toLowerCase().replaceAll(" ","-")}`}>{s.priority}</span></div><p>{s.need}</p><small>{s.why}</small></article>)}</div>
          <h3>Demand signals</h3>
          <div className="market-signals">{data.signals.map((s) => <article key={s.title}><b>{s.title}</b><p>{s.detail}</p><a href={s.url} target="_blank" rel="noreferrer">{s.source} ↗</a></article>)}</div>
        </>}
        {tab === "economics" && <>
          <div className="market-model-note"><b>Model, not a promise.</b> Udyam registrations are not treated as active customers. The reachable market is an explicit hypothesis: {model.serviceable_share_pct}% of Udyam registrations as recurring-contract businesses, then {model.reachable_share_of_serviceable_pct}% reachable through initial channels. This implies approximately {Math.round(reachable).toLocaleString("en-IN")} potential MSME accounts to test, not a verified TAM. Registered-user targets also include adjacent freelancer and lawyer segments not counted in this MSME-only estimate.</div>
          <div className="market-controls"><label>Scenario<select value={scenario} onChange={(e) => {setScenario(e.target.value);setMonthlyPrice(model.scenarios[e.target.value].monthly_arpa);}}><option value="conservative">Conservative</option><option value="base">Base case</option><option value="aggressive">Aggressive</option></select></label><label>Blended monthly revenue per paying account<input type="number" min="199" max="25000" step="100" value={monthlyPrice} onChange={(e) => setMonthlyPrice(Math.max(0, Number(e.target.value)||0))}/></label></div>
          <div className="market-table-wrap"><table className="market-table"><thead><tr><th>Metric</th>{rows.map((r) => <th key={r.year}>{r.year}</th>)}</tr></thead><tbody>
            <tr><td>Registered users (cumulative)</td>{rows.map((r) => <td key={r.year}>{r.registered_users.toLocaleString("en-IN")}</td>)}</tr>
            <tr><td>Paying accounts (year-end)</td>{rows.map((r) => <td key={r.year}>{r.paying_customers.toLocaleString("en-IN")}</td>)}</tr>
            <tr><td>Paid conversion of registered base</td>{rows.map((r) => <td key={r.year}>{r.conversion.toFixed(1)}%</td>)}</tr>
            <tr><td>Recognised revenue (annualised run-rate proxy)</td>{rows.map((r) => <td key={r.year}><b>{compact(r.annualRevenue)}</b></td>)}</tr>
            <tr><td>Year-end ARR</td>{rows.map((r) => <td key={r.year}><b>{compact(r.arr)}</b></td>)}</tr>
          </tbody></table></div>
          <h3>Indicative pricing ladder</h3><div className="market-pricing">{model.pricing_ladder.map((p) => <article key={p.name}><b>{p.name}</b><strong>{p.price}</strong><small>{p.role}</small></article>)}</div>
          <div className="market-model-note"><b>Unit economics to test:</b> gross margin {model.cost_assumptions.gross_margin_pct}% · monthly logo churn {model.cost_assumptions.monthly_logo_churn_pct}% · blended CAC {fmt(model.cost_assumptions.blended_cac_inr)}. {model.cost_assumptions.note} These are assumptions, not observed Maatamudra metrics.</div>
          <p className="muted">Revenue calculation: average of prior-year and year-end paying accounts × blended monthly price × 12. ARR = year-end paying accounts × blended monthly price × 12. Excludes GST, discounts, refunds, services revenue and operating expenses.</p>
        </>}
        {tab === "competition" && <>
          <h3>Competitive landscape</h3><p className="muted">Positioning hypotheses based on public product positioning. This is not a feature-by-feature product audit or pricing comparison.</p>
          <div className="market-competitors">{data.competitors.map((c) => <article key={c.name}><div><h4>{c.name}</h4><span>{c.category}</span></div><p><b>Strength</b><br/>{c.strength}</p><p><b>Maatamudra opportunity</b><br/>{c.opening}</p><a href={c.url} target="_blank" rel="noreferrer">Visit product ↗</a></article>)}</div>
        </>}
        {tab === "iterations" && <>
          <div className="iteration-banner"><div><span className="section-kicker">RESEARCH SPRINT {iteration+1} / {data.research_iterations.length} · {completed.length} COMPLETED</span><h3>{current.title}</h3><p>{current.objective}</p></div><button className="primary" onClick={() => {setCompleted((v)=>[...v,iteration]);setIteration((v)=>(v+1)%data.research_iterations.length);}}>Complete sprint &amp; open next →</button></div>
          <div className="iteration-tasks">{current.tasks.map((t,i) => <label key={t}><input type="checkbox"/> <span>{t}</span></label>)}</div>
          <div className="market-model-note"><b>Exit criteria:</b> {current.exit}</div>
          <h3>Evidence and iteration discipline</h3><p>Use each cycle to replace assumptions with observed data. Record interview counts, segment, problem frequency, willingness to pay, activation, repeat usage, churn and acquisition cost. Do not upgrade a hypothesis to a verified market fact merely because the model produces an attractive revenue figure.</p>
          <div className="iteration-steps">{data.research_iterations.map((it,i)=><button key={it.title} className={i===iteration?"active":""} onClick={()=>setIteration(i)}>{i+1}. {it.title}</button>)}</div>
        </>}
        <footer className="market-foot"><span>Sources and assumptions updated: {data.research_as_of} · {data.version}</span><span>{data.disclaimer}</span></footer>
      </section>
    </div>
  );
}

function CMap({ map }) {
  if (!map?.available) return map?.reason ? <p className="muted">{map.reason}</p> : null;
  const W = 360, H = 150, P = 28;
  const xs = map.series.map((p) => p.x), ys = map.series.map((p) => p.y);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y1 = Math.max(1, ...ys);
  const X = (x) => P + ((x - x0) / Math.max(1, x1 - x0)) * (W - P - 6);
  const Y = (y) => H - P - (y / y1) * (H - P - 10);
  const cls = (l) => /default/i.test(l) ? "z-bad" : /no consequence|ended/i.test(l) ? "z-none" : "z-warn";
  const pts = map.series.map((p) => `${X(p.x)},${Y(p.y)}`).join(" ");
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${map.title}: ${map.findings[0] || ""}`} className="cmap">
        {map.zones.map((z, i) => <rect key={i} x={X(z.from)} y="6" width={Math.max(2, X(z.to + (map.series[1]?.x - map.series[0]?.x || 1)) - X(z.from))} height={H - P - 6} className={cls(z.label)} />)}
        <polyline points={pts} fill="none" stroke="var(--ink)" strokeWidth="2" />
        <text x={P} y={H - 8} fontSize="10" fill="var(--muted)">{map.x_label}: {x0} to {x1}</text>
        <text x="2" y="14" fontSize="10" fill="var(--muted)">{map.y_label} max {y1.toLocaleString("en-IN")}</text>
      </svg>
      <div className="legend">{map.zones.map((z, i) => <span key={i}><i className={cls(z.label)} /> {z.label} ({z.from} to {z.to})</span>)}</div>
      <ul className="finds">{map.findings.map((f, i) => <li key={i}>{f}</li>)}</ul>
    </div>
  );
}

function Ask({ contract, run, busy, setSel }) {
  const [q, setQ] = useState("");
  const [res, setRes] = useState(null);
  useEffect(() => { setQ(""); setRes(null); }, [contract.id, contract.updated_at]);
  const ask = (text) => run("ask", async () => { setRes(await api.ask(contract.id, text)); });
  const chips = ["What happens if I pay late?", "Can either side end this early, and what does it cost?", "Which clause is the riskiest for me?"];
  return (
    <>
      <p className="muted">Ask in plain words. The assistant reads this agreement and runs the time machine; its answer is checked against the agreement.</p>
      <div className="row"><input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && q && ask(q)} placeholder="Ask about this agreement" aria-label="Question" />
        <button className="primary" disabled={!q || !!busy} onClick={() => ask(q)}>{busy === "ask" ? "…" : "Ask"}</button></div>
      <div className="row" style={{ flexWrap: "wrap" }}>{chips.map((c) => <button key={c} onClick={() => { setQ(c); ask(c); }}>{c}</button>)}</div>
      {res && (
        <div className="card">
          <p style={{ whiteSpace: "pre-wrap" }}>{res.answer.replace(/\[clause:[A-Za-z0-9_]+\]/g, "")}</p>
          <div>{res.citations.map((k) => <button key={k} onClick={() => setSel(k)} style={{ marginRight: 4 }}>{k.replace(/_/g, " ")}</button>)}</div>
          {res.warnings.map((w, i) => <div className="err" key={i}>{w}</div>)}
          {res.trace.length > 0 && <details><summary>How this was found</summary>
            {res.trace.map((t, i) => <p key={i} className="muted"><b>{t.tool}</b> {JSON.stringify(t.args)}</p>)}</details>}
        </div>
      )}
    </>
  );
}

function Explain({ contract, run, busy }) {
  const [lang, setLang] = useState("English");
  const [res, setRes] = useState(null);
  const [note, setNote] = useState("");
  useEffect(() => { setRes(null); setNote(""); }, [contract.id, contract.updated_at]);
  const go = () => run("explain", async () => { setNote(""); setRes(await api.explain(contract.id, lang)); });
  const say = (it) => setNote(speak([it.plain, it.you_must, it.watch_out].filter(Boolean).join(". "), res.speech_lang));
  return (
    <>
      <p className="muted">A plain-language explanation of each clause. The English clause is the agreement.</p>
      <div className="row"><select value={lang} onChange={(e) => setLang(e.target.value)} aria-label="Language">{["English", "Assamese", "Bengali", "Bodo", "Dogri", "Gujarati", "Hindi", "Kannada", "Kashmiri", "Konkani", "Maithili", "Malayalam", "Manipuri", "Marathi", "Nepali", "Odia", "Punjabi", "Sanskrit", "Santali", "Sindhi", "Tamil", "Telugu", "Urdu"].map((l) => <option key={l}>{l}</option>)}</select>
        <button className="primary" disabled={!!busy} onClick={go}>{busy === "explain" ? "Explaining…" : "Explain"}</button></div>
      {note && <div className="err">{note}</div>}
      {res && <><p><b>{res.summary}</b></p>
        {res.items.map((it) => (
          <div className="card" key={it.clause_key}>
            <b>{it.title}</b> {!it.numbers_ok && <span className="chip high">numbers differ: read the English clause</span>}
            <p>{it.plain}</p>{it.you_must && <p><b>You must:</b> {it.you_must}</p>}{it.watch_out && <p><b>Watch out:</b> {it.watch_out}</p>}
            <button onClick={() => say(it)} aria-label="Read aloud">🔊 Read aloud</button>
          </div>))}
        <p className="muted">{res.note}</p></>}
    </>
  );
}

function Evidence({ contract, clause, setContract, run, busy, setErr }) {
  const [statutes, setStatutes] = useState({});
  useEffect(() => {
    let active = true;
    setStatutes({});
    api.statutes(contract.id)
      .then((result) => { if (active) setStatutes(result); })
      .catch((e) => { if (active) setErr(e.message); });
    return () => { active = false; };
  }, [contract.id, contract.updated_at, setErr]);
  if (!clause) return null;
  const ev = contract.evidence.filter((e) => e.clause_key === clause.key);
  const gather = () => run("ev", async () => { await api.evidence(contract.id, clause.key); setContract(await api.get(contract.id)); });
  return (
    <>
      <h3>{clause.title}</h3>
      {(statutes[clause.key] || []).map((s) => (
        <div className="card" key={s.key}>
          <b>{s.act}, s.{s.section}</b> <Chip v={s.verified ? "verified" : "needs_verification"} />
          <p>{s.summary}</p>
          <a href={s.source_url} target="_blank" rel="noreferrer">Official text</a>
        </div>
      ))}
      {clause.evidence_queries.length > 0 ? (
        <div className="row"><button className="primary" disabled={!!busy} onClick={gather}>
          {busy === "ev" ? "Checking judgments…" : "Find and check case law"}</button></div>
      ) : <p className="muted">No case-law check is defined for this clause.</p>}
      {ev.map((e) => (
        <div className="card" key={e.id}>
          <b>{e.title}</b> <Chip v={e.status} />
          <p className="muted">{e.court} {e.date} {e.source === "tavily" && "· found by web search; the passage is a snippet, open the judgment to confirm"}</p>
          {e.passage && <div className="passage">{e.passage}</div>}
          <p>{e.judge_reason}</p>
          <a href={e.url} target="_blank" rel="noreferrer">Open judgment</a>
        </div>
      ))}
    </>
  );
}

function LegalContext({ contract }) {
  const [report, setReport] = useState(null);
  const [err, setErr] = useState("");
  const [targetLang, setTargetLang] = useState("Hindi");
  const [translated, setTranslated] = useState("");
  const [translationCheck, setTranslationCheck] = useState(null);
  const [translating, setTranslating] = useState(false);
  useEffect(() => {
    let active = true;
    setReport(null);
    setErr("");
    setTranslated("");
    setTranslationCheck(null);
    api.legalIntelligence(contract.id)
      .then((result) => { if (active) setReport(result); })
      .catch((e) => { if (active) setErr(e.message); });
    return () => { active = false; };
  }, [contract.id, contract.updated_at]);
  const translateReport = async () => {
    setTranslating(true); setTranslated("");
    try { const text = (report.findings || []).map((f) => `${f.title}\n${f.message}\nLegal basis: ${(f.legal_basis || []).join(", ")}`).join("\n\n");
      const result = await api.translate(text, targetLang, "English"); setTranslated(result.translated_text); setTranslationCheck(result);
    } catch (e) { setErr(e.message); } finally { setTranslating(false); }
  };
  if (err) return <div className="err">{err}</div>;
  if (!report) return <p className="muted">Checking the agreement against the India legal context…</p>;
  return <>
    <h3>Indian legal context</h3>
    <p className="muted">{report.jurisdiction.state_ut || "State/UT not selected"} · Pan-India legal-source registry · {report.summary.total} review prompts</p>
    <div className="card">
      <b>Explain findings in an Indian language</b>
      <div className="row"><select value={targetLang} onChange={(e) => setTargetLang(e.target.value)} aria-label="Translation language">{["Assamese","Bengali","Bodo","Dogri","Gujarati","Hindi","Kannada","Kashmiri","Konkani","Maithili","Malayalam","Manipuri","Marathi","Nepali","Odia","Punjabi","Sanskrit","Santali","Sindhi","Tamil","Telugu","Urdu"].map((l) => <option key={l}>{l}</option>)}</select><button className="primary" onClick={translateReport} disabled={translating}>{translating ? "Translating…" : "Translate legal findings"}</button></div>
      {translated && <><p style={{whiteSpace:"pre-wrap"}}>{translated}</p>{translationCheck && !translationCheck.number_integrity && <p className="field-hint">Warning: some numbers differ or are missing in the translation. Verify every amount, date and section reference against the English source.</p>}</>}
      <p className="field-hint">AI translation is informational, not certified. Preserve the original legal text for signing and legal reliance.</p>
    </div>
    <div className="card"><b>Coverage transparency</b><p>Official registration portal: {report.jurisdiction.registration_portal ? <a href={report.jurisdiction.registration_portal} target="_blank" rel="noreferrer">Open state/UT portal ↗</a> : "Not listed in the national directory"}</p><p className="muted">{report.jurisdiction.digital_e_stamp_status || "Select a State/UT."}. State stamp schedules, exemptions, tenancy rules and labour rules still require instrument-specific Gazette verification. Maatamudra does not invent rates.</p><p className="field-hint">Portal directory: <a href="https://ngdrs.gov.in/NGDRS_Website/state_ut_links.php" target="_blank" rel="noreferrer">Department of Land Resources / NGDRS</a> · e-stamping directory: <a href="https://www.nesl.co.in/states-union-territories-for-digital-e-stamping/" target="_blank" rel="noreferrer">NeSL</a></p></div>
    <div className="stats-row"><span><b>{report.summary.high}</b> high</span><span><b>{report.summary.medium}</b> medium</span><span><b>{report.summary.coverage_gaps}</b> coverage gaps</span></div>
    {report.findings.map((f) => <div className="card" key={f.id}>
      <div className="row"><b>{f.title}</b><Chip v={f.severity} /></div>
      <p>{f.message}</p>
      {f.legal_basis?.length > 0 && <p className="muted">Legal basis: {f.legal_basis.join(" · ")}</p>}
      <p><b>Next step:</b> {f.recommended_action}</p>
      <a href={f.source_url} target="_blank" rel="noreferrer">Open source / official legal portal ↗</a>
      <p className="field-hint">{f.verification}</p>
    </div>)}
    <details className="card"><summary>Central legislation catalogue</summary>{report.central_laws_catalogue.map((law) => <p key={law.id}><b>{law.name}</b><br/><span className="muted">{law.topics.join(" · ")} — {law.status}</span><br/><a href={law.source} target="_blank" rel="noreferrer">Source ↗</a></p>)}</details>
    <p className="field-hint">{report.notice}</p>
  </>;
}

function Review({ contract, clause, setContract, run, busy, setSel, td, setErr }) {
  const [lint, setLint] = useState(null);
  const [side, setSide] = useState("customer / buyer");
  const [deadline, setDeadline] = useState("");
  const [focus, setFocus] = useState("Liability, indemnity, termination, payment and data protection");
  const [dealContext, setDealContext] = useState("");
  const [pbResult, setPbResult] = useState(null);
  const [ndaResult, setNdaResult] = useState(null);
  const [playbook, setPlaybook] = useState(null);
  useEffect(() => { setPbResult(null); setNdaResult(null); }, [contract.id, contract.updated_at]);
  useEffect(() => {
    let active = true;
    api.playbook().then((result) => { if (active) setPlaybook(result); }).catch((e) => { if (active) setErr(e.message); });
    return () => { active = false; };
  }, [setErr]);
  const contractText = (contract.clauses || []).map((c) => `${c.title}\n${c.text}`).join("\n\n");
  const runPlaybook = () => run("playbook", async () => setPbResult(await api.playbookReview(contract.id, { side, deadline: deadline || "not specified", focus_areas: focus.split(",").map(x => x.trim()).filter(Boolean), deal_context: dealContext || "not provided" })));
  const runNda = () => run("nda", async () => setNdaResult(await api.ndaTriage(contractText)));
  useEffect(() => {
    let active = true;
    setLint(null);
    api.lint(contract.id)
      .then((result) => { if (active) setLint(result); })
      .catch((e) => { if (active) setErr(e.message); });
    return () => { active = false; };
  }, [contract.id, contract.updated_at, setErr]);
  const reds = contract.redlines;
  const r = reds.find((x) => x.clause_key === clause?.key);
  const decide = (d) => run("decide", async () => setContract(await api.decide(contract.id, r.clause_key, d)));
  const cap = (s) => s ? s[0].toUpperCase() + s.slice(1) : "";
  return (
    <>
      <h3>Automatic checks</h3>
      {lint === null && <p className="muted">Refreshing automatic checks…</p>}
      {lint?.length === 0 && <p className="muted">Nothing flagged.</p>}
      {lint?.map((f, i) => (
        <button key={i} className="card" style={{ display: "block", width: "100%", textAlign: "left" }} onClick={() => setSel(f.clause_key)}>
          <Chip v={f.severity} /> {f.message}
        </button>
      ))}
      <h3 style={{ marginTop: 16 }}>Playbook-based contract review</h3>
      <p className="muted">Compare this draft with an illustrative negotiation playbook. Add your side and deal priorities; the playbook is a configurable preference framework, not a statement of Indian law.</p>
      <div className="card">
        <label>Your side</label><select value={side} onChange={e => setSide(e.target.value)}><option>customer / buyer</option><option>vendor / supplier</option><option>licensor</option><option>licensee</option><option>employer</option><option>employee</option><option>landlord</option><option>tenant</option><option>partner</option><option>not specified</option></select>
        <label>Target signing / review deadline</label><input value={deadline} onChange={e => setDeadline(e.target.value)} placeholder="e.g. 30 November 2026" />
        <label>Focus areas (comma separated)</label><input value={focus} onChange={e => setFocus(e.target.value)} />
        <label>Deal context</label><textarea value={dealContext} onChange={e => setDealContext(e.target.value)} placeholder="Deal value, relationship, leverage, must-have terms, acceptable compromises…" rows={3} />
        <button className="primary" disabled={!!busy} onClick={runPlaybook}>{busy === "playbook" ? "Reviewing against playbook…" : "Run playbook review"}</button>
      </div>
      {playbook && <details className="card"><summary>View default playbook and risk rules</summary><p className="muted">{playbook.notice}</p>{playbook.positions.map(p => <p key={p.id}><b>{p.topic}:</b> {p.default_position}<br/><span className="muted">Escalate: {p.escalation_triggers.join("; ")}</span></p>)}</details>}
      {pbResult && <div className="card"><div className="row"><b>Overall playbook risk</b><Chip v={pbResult.overall_risk.toLowerCase()} /></div><p>{pbResult.executive_summary}</p>
        <h4>Clause findings</h4>{pbResult.clause_findings.map((f,i)=><div key={i}><b>{f.clause || f.topic || `Finding ${i+1}`}</b> <Chip v={(f.risk || "yellow").toLowerCase()} /><p>{f.deviation || f.issue || f.analysis}</p>{f.business_impact && <p><b>Business impact:</b> {f.business_impact}</p>}{f.recommendation && <p><b>Recommendation:</b> {f.recommendation}</p>}</div>)}
        {pbResult.negotiation_priorities?.length>0 && <><h4>Negotiation priorities</h4><ul>{pbResult.negotiation_priorities.map((x,i)=><li key={i}>{x}</li>)}</ul></>}
        {pbResult.redline_suggestions?.length>0 && <><h4>Suggested fallback language</h4>{pbResult.redline_suggestions.map((x,i)=><div key={i}><b>{x.clause || `Suggestion ${i+1}`}</b><p>{x.suggested_text || x.redline || x.text}</p></div>)}</>}
        {pbResult.open_questions?.length>0 && <><h4>Questions to resolve</h4><ul>{pbResult.open_questions.map((x,i)=><li key={i}>{x}</li>)}</ul></>}
        <p className="field-hint">{pbResult.disclaimer}</p></div>}
      {td?.key === "nda" && <><h3>NDA pre-screen</h3><p className="muted">GREEN / YELLOW / RED checklist triage. It is a preliminary screen, not approval to sign.</p><button disabled={!!busy} onClick={runNda}>{busy === "nda" ? "Screening NDA…" : "Run NDA triage"}</button>{ndaResult && <div className="card"><div className="row"><b>{ndaResult.classification} — {ndaResult.summary}</b><Chip v={ndaResult.classification.toLowerCase()} /></div>{ndaResult.findings.map((f,i)=><p key={i}><Chip v={f.status.toLowerCase()} /> <b>{f.id}</b>: {f.concern} {f.evidence && `Evidence: ${f.evidence}`}</p>)}{ndaResult.escalation_reasons?.map((x,i)=><p key={i}>{x}</p>)}<p className="field-hint">{ndaResult.disclaimer}</p></div>}</>}
      <h3 style={{ marginTop: 16 }}>Review both sides</h3>
      <div className="row"><button className="primary" disabled={!!busy} onClick={() => run("review", async () => setContract(await api.review(contract.id)))}>
        {busy === "review" ? `${cap(td?.party_a)}, ${td?.party_b} and neutral reviewer are working…` : "Run review"}</button></div>
      <p className="muted">Check case law first for the clauses you care about. The neutral reviewer cites only verified judgments.</p>
      {reds.map((x) => <button key={x.clause_key} onClick={() => setSel(x.clause_key)} style={{ margin: "0 4px 4px 0" }}>
        {x.clause_key.replace("_", " ")} <Chip v={x.status} /></button>)}
      {r && (
        <div className="card">
          <p><b>Risk to {td?.party_a}:</b> {r.risk_to_party_a}</p>
          <p><b>Risk to {td?.party_b}:</b> {r.risk_to_party_b}</p>
          <p><b>Ask a lawyer:</b> {r.legal_question}</p>
          <div className="diff">{wordDiff(r.original, r.proposed).map((d, i) => <span key={i} className={d.t === "same" ? "" : d.t}>{d.w} </span>)}</div>
          <p>{r.rationale}</p>
          {r.evidence_ids.length > 0 && <p className="muted">Backed by {r.evidence_ids.length} verified judgment(s).</p>}
          {r.warning && <div className="err">{r.warning}</div>}
          {r.status === "pending" && <div className="row">
            <button className="primary" disabled={!!r.warning || !!busy} onClick={() => decide("accept")}>Accept change</button>
            <button disabled={!!busy} onClick={() => decide("reject")}>Keep original</button></div>}
        </div>
      )}
    </>
  );
}

function TimeMachine({ contract, run, busy, td, setErr }) {
  const scenarios = td?.scenarios || [];
  const [idx, setIdx] = useState(0);
  const sc = scenarios[idx];
  const defaults = (s) => Object.fromEntries((s?.inputs || []).map((i) => [i.name, i.default]));
  const [vals, setVals] = useState(defaults(sc));
  const [out, setOut] = useState(null);
  useEffect(() => { setIdx(0); setVals(defaults(scenarios[0])); setOut(null); }, [td?.key]);
  const [cmap, setCmap] = useState(null);
  useEffect(() => {
    let active = true;
    setCmap(null);
    setOut(null);
    api.map(contract.id)
      .then((result) => { if (active) setCmap(result); })
      .catch((e) => { if (active) setErr(e.message); });
    return () => { active = false; };
  }, [contract.id, contract.updated_at, setErr]);
  if (!sc) return <div className="card"><b>Scenario testing is coming soon for this agreement type.</b><p className="muted">No dates or amounts are simulated here; use the written terms and ask a lawyer to review the consequences.</p></div>;
  const change = (i) => { setIdx(i); setVals(defaults(scenarios[i])); setOut(null); };
  const go = () => run("sim", async () => {
    const body = { type: sc.type, ...(sc.fixed || {}) };
    sc.inputs.forEach((i) => {
      const v = vals[i.name];
      body[i.name] = i.name === "fully_paid" ? v === "yes" : i.kind === "range" || i.kind === "number" ? Number(v) : v;
    });
    setOut(await api.simulate(contract.id, body));
  });
  return (
    <>
      <h3>Consequence map</h3>
      <CMap map={cmap} />
      <h3 style={{ marginTop: 16 }}>Try a scenario</h3>
      <p className="muted">See what this agreement's own terms say if things go differently.</p>
      <select value={idx} onChange={(e) => change(Number(e.target.value))} aria-label="Scenario">
        {scenarios.map((s, i) => <option key={s.type} value={i}>{s.label}</option>)}
      </select>
      {sc.inputs.map((i) => (
        <div className="row" key={i.name}>
          <label style={{ minWidth: 110 }}>{i.label}</label>
          {i.kind === "select" ? (
            <select value={vals[i.name]} onChange={(e) => setVals({ ...vals, [i.name]: e.target.value })}>{i.options.map((o) => <option key={o}>{o}</option>)}</select>
          ) : i.kind === "range" ? (
            <><input type="range" min={i.min} max={i.max} value={vals[i.name]} onChange={(e) => setVals({ ...vals, [i.name]: e.target.value })} /><b>{vals[i.name]}</b></>
          ) : (
            <input type={i.kind === "date" ? "date" : "number"} value={vals[i.name]} onChange={(e) => setVals({ ...vals, [i.name]: e.target.value })} />
          )}
        </div>
      ))}
      <button className="primary" disabled={!!busy} onClick={go}>Show what happens</button>
      {out && (
        <div style={{ marginTop: 12 }}>
          {Object.keys(HEADLINES).filter((k) => out[k] != null).map((k) => <div className="big" key={k}>{HEADLINES[k]}: {money(k, out[k])}</div>)}
          <div className="timeline">{out.events.map((e, i) => <div key={i}><b>{e.date}</b><br />{e.label}</div>)}</div>
          {out.notes.map((n, i) => <p key={i}>{n}</p>)}
          <p className="muted">{out.disclaimer}</p>
        </div>
      )}
    </>
  );
}

function Execution({ contract, setContract, run, setErr }) {
  const [ex, setEx] = useState(null);
  const [notes, setNotes] = useState({});
  const [signingDemo, setSigningDemo] = useState(null);
  const [signingBusy, setSigningBusy] = useState(false);
  useEffect(() => {
    let active = true;
    setEx(null);
    setNotes({});
    setSigningDemo(null);
    api.execution(contract.id)
      .then((result) => { if (active) setEx(result); })
      .catch((e) => { if (active) setErr(e.message); });
    return () => { active = false; };
  }, [contract.id, contract.updated_at, setErr]);
  const stepFor = { stamp_duty: "stamp_duty_verified", registration: "registration_completed", signing: "signed_by_parties", lawyer: "legal_review_completed" };
  if (!ex) return null;
  if (!ex.supported) return <div className="err">{ex.message}</div>;
  return (
    <>
      <p className="muted">{ex.disclaimer} A step is ticked only when you record the evidence.</p>
      <div className="card"><b>Digital signing provider hand-off (simulated)</b><p className="muted">This demonstrates where an authorized eSign provider would be connected. It does not authenticate signers or apply a signature.</p><button onClick={async () => { setSigningBusy(true); try { setSigningDemo(await api.demoSigning(contract.id)); } catch (e) { setErr(e.message); } finally { setSigningBusy(false); } }}>{signingBusy ? "Simulating provider flow…" : "Preview signing workflow"}</button>{signingDemo && <><p><b>{signingDemo.status}</b></p><ol>{signingDemo.steps.map((s,i)=><li key={i}>{s}</li>)}</ol><p className="field-hint">{signingDemo.notice}</p></>}</div>
      {ex.items.map((it) => (
        <div className="card" key={it.id}>
          <b>{it.title}</b> <Chip v={it.done ? "accepted" : it.rule_status} />
          <p>{it.guidance}</p>
          {it.source_url && <a href={it.source_url} target="_blank" rel="noreferrer">Official source</a>}
          {!it.done && stepFor[it.id] && <div className="row">
            <input placeholder="Evidence: receipt no., date, who confirmed" value={notes[it.id] || ""} onChange={(e) => setNotes({ ...notes, [it.id]: e.target.value })} />
            <button disabled={(notes[it.id] || "").trim().length < 5}
              onClick={() => run("c", async () => setContract(await api.confirm(contract.id, stepFor[it.id], notes[it.id])))}>Record</button></div>}
        </div>
      ))}
    </>
  );
}
