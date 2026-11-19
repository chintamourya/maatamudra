const BASE = import.meta.env.VITE_API_URL || "";
async function call(path, opts = {}) {
  const r = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (!r.ok) {
    const e = await r.json().catch(() => ({}));
    throw new Error(typeof e.detail === "string" ? e.detail : `Request failed (${r.status})`);
  }
  return r.json();
}
export const api = {
  health: () => call("/api/health"),
  marketResearch: () => call("/api/market-research"),
  translate: (text, target_language, source_language = "auto") => call("/api/translate", { method: "POST", body: { text, target_language, source_language } }),
  demoAuth: (user_label, role) => call("/api/demo/auth/session", { method: "POST", body: { user_label, role } }),
  demoSigning: (contract_id) => call("/api/demo/signing/session", { method: "POST", body: { contract_id } }),
  ask: (id, question) => call(`/api/contracts/${id}/ask`, { method: "POST", body: { question } }),
  explain: (id, language) => call(`/api/contracts/${id}/explain`, { method: "POST", body: { language } }),
  map: (id) => call(`/api/contracts/${id}/consequence-map`),
  uploadAnalyze: (body) => call("/api/upload/analyze", { method: "POST", body }),
  uploadOpen: (body) => call("/api/upload/contract", { method: "POST", body }),
  types: () => call("/api/types"),
  jurisdictions: () => call("/api/jurisdictions"),
  legalIntelligence: (id) => call(`/api/contracts/${id}/legal-intelligence`),
  legalCoverage: () => call("/api/legal/coverage"),
  lint: (id) => call(`/api/contracts/${id}/lint`),
  obligations: (id) => call(`/api/contracts/${id}/obligations`),
  icsUrl: (id) => `${BASE}/api/contracts/${id}/calendar.ics`,
  jsonUrl: (id) => `${BASE}/api/contracts/${id}/obligations`,
  intake: (message, spec, previous_questions = []) => call("/api/intake", { method: "POST", body: { message, spec, previous_questions } }),
  create: (spec) => call("/api/contracts", { method: "POST", body: spec }),
  get: (id) => call(`/api/contracts/${id}`),
  statutes: (id) => call(`/api/contracts/${id}/statutes`),
  evidence: (id, key) => call(`/api/contracts/${id}/evidence/${key}`, { method: "POST" }),
  review: (id) => call(`/api/contracts/${id}/review`, { method: "POST" }),
  copilotReview: (id) => call(`/api/contracts/${id}/copilot/review`, { method: "POST" }),
  copilotRewrite: (id, clause_key, instruction) => call(`/api/contracts/${id}/copilot/rewrite`, { method: "POST", body: { clause_key, instruction } }),
  copilotApply: (id, suggestion_id) => call(`/api/contracts/${id}/copilot/apply`, { method: "POST", body: { suggestion_id } }),
  copilotDismiss: (id, suggestion_id) => call(`/api/contracts/${id}/copilot/suggestions/${suggestion_id}/dismiss`, { method: "POST" }),
  copilotApplyTerm: (id, suggestion_id) => call(`/api/contracts/${id}/copilot/terms/apply`, { method: "POST", body: { suggestion_id } }),
  copilotDismissTerm: (id, suggestion_id) => call(`/api/contracts/${id}/copilot/terms/${suggestion_id}/dismiss`, { method: "POST" }),
  playbook: () => call("/api/legal/playbook"),
  playbookReview: (id, body) => call(`/api/contracts/${id}/playbook-review`, { method: "POST", body }),
  ndaTriage: (text) => call("/api/legal/nda-triage", { method: "POST", body: { text } }),
  decide: (id, key, d) => call(`/api/contracts/${id}/redlines/${key}/${d}`, { method: "POST" }),
  simulate: (id, scenario) => call(`/api/contracts/${id}/simulate`, { method: "POST", body: scenario }),
  execution: (id) => call(`/api/contracts/${id}/execution`),
  confirm: (id, step, note) => call(`/api/contracts/${id}/execution/confirm`, { method: "POST", body: { step, note, done: true } }),
  docxUrl: (id) => `${BASE}/api/contracts/${id}/docx`,
};
