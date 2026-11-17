// "Explain availability" UI. Never computes or changes availability: the deterministic result card
// (#result) is produced by the original script; this file only asks the server for a wording of it.
"use strict";
(function () {
  const $ = (id) => document.getElementById(id);
  const result = $("result"), box = $("explainBox"), btn = $("explainBtn");
  let snap = null;                                   // inputs at the moment the result was shown
  let seq = 0;                                       // ignores answers to outdated requests

  function reset() {
    seq++;
    $("explainOut").hidden = true;
    btn.disabled = false;
    btn.textContent = "Explain availability";
  }
  function heading() { const b = result.querySelector(".big"); return b ? b.textContent : ""; }

  // The original script re-renders #result on every check: capture the inputs it was based on.
  new MutationObserver(() => {
    reset();
    const ok = result.classList.contains("available") || result.classList.contains("unavailable");
    box.hidden = !ok;
    snap = ok ? {start: $("start").value, end: $("end").value, blocked: $("blockedToggle").checked} : null;
  }).observe(result, {attributes: true, childList: true, subtree: true});
  // A changed input or the blocked toggle makes the shown status stale: hide the explanation.
  $("form").addEventListener("input", () => { box.hidden = true; reset(); });

  const SRC = {mock: "Mock demo adapter", llm: "AI model", fallback: "Standard message (assistant unavailable)"};
  function show(text, src, note) {
    $("explainText").textContent = text;               // textContent: model output is never parsed as HTML
    $("explainSrc").textContent = SRC[src] || "Unverified source";
    $("explainNote").textContent = note;
    $("explainOut").hidden = false;
  }

  btn.addEventListener("click", async () => {
    if (!snap) return;
    const mine = ++seq, shown = heading();
    btn.disabled = true; btn.textContent = "Generating...";
    const ctrl = new AbortController(), timer = setTimeout(() => ctrl.abort(), 6000);
    try {
      const r = await fetch("/api/explain", {method: "POST", headers: {"Content-Type": "application/json"},
                                            body: JSON.stringify(snap), signal: ctrl.signal});
      const data = await r.json();
      if (mine !== seq) return;
      if (!r.ok) { show("An explanation cannot be generated for this input. " + (data.error ? data.error.message + "." : ""),
                        "fallback", "The status above is unchanged."); return; }
      if (data.decision.label !== shown) {             // server and page disagree: show nothing generated
        show("The explanation service gave a different status than this page, so no explanation is shown.",
             "fallback", "The status above is unchanged."); return; }
      show(data.explanation.text, data.explanation.source,
           data.disclaimer + (data.explanation.generated ? "" : " (Generated text was not used.)"));
    } catch (e) {
      if (mine !== seq) return;
      show("An explanation is not available right now.", "fallback",
           "The status above is unchanged. This explanation is not a booking confirmation.");
    } finally {
      clearTimeout(timer);
      if (mine === seq) { btn.disabled = false; btn.textContent = "Explain again"; }
    }
  });
})();
