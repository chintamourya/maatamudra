// Browser voice helpers (Web Speech API). Support varies by browser and installed voices.
export const LANGS = [
  ["en-IN", "English"], ["as-IN", "Assamese"], ["bn-IN", "বাংলা"], ["brx-IN", "Bodo"],
  ["doi-IN", "Dogri"], ["gu-IN", "ગુજરાતી"], ["hi-IN", "हिन्दी"], ["kn-IN", "ಕನ್ನಡ"],
  ["ks-IN", "Kashmiri"], ["kok-IN", "Konkani"], ["mai-IN", "Maithili"], ["ml-IN", "മലയാളം"],
  ["mni-IN", "Manipuri"], ["mr-IN", "मराठी"], ["ne-IN", "नेपाली"], ["or-IN", "ଓଡ଼ିଆ"],
  ["pa-IN", "ਪੰਜਾਬੀ"], ["sa-IN", "Sanskrit"], ["sat-IN", "Santali"], ["sd-IN", "Sindhi"],
  ["ta-IN", "தமிழ்"], ["te-IN", "తెలుగు"], ["ur-IN", "اردو"],
];
const SR = typeof window !== "undefined" && (window.SpeechRecognition || window.webkitSpeechRecognition);
export const canListen = !!SR;

export function listen(lang, onText, onEnd) {
  const r = new SR();
  r.lang = lang; r.interimResults = false; r.continuous = false;
  r.onresult = (e) => onText(Array.from(e.results).map((x) => x[0].transcript).join(" "));
  r.onend = onEnd; r.onerror = onEnd;
  r.start();
  return r;
}

export function speak(text, lang) {
  if (!("speechSynthesis" in window)) return "This browser cannot read aloud.";
  const base = lang.slice(0, 2);
  const has = window.speechSynthesis.getVoices().some((v) => v.lang.toLowerCase().startsWith(base));
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang;
  window.speechSynthesis.speak(u);
  return has ? "" : "No voice for this language was found on this device, so it may sound wrong or stay silent.";
}
