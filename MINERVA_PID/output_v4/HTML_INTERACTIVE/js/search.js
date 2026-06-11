/* MINERVA P&ID v4 - tag search.
 * Indexes every <text> node in the active SVG and lets the user jump to /
 * highlight a tag (instrument bubble, valve, line name, terminal point). */
(function () {
  "use strict";
  let entries = [];        // {text, el}
  let lastHL = null;

  function index(svg) {
    entries = [];
    svg.querySelectorAll("text").forEach(t => {
      const s = (t.textContent || "").trim();
      if (s.length >= 1 && s.length <= 40) entries.push({ text: s, el: t });
    });
  }

  function clearHL() {
    if (lastHL) { lastHL.classList.remove("hl"); lastHL = null; }
  }

  function jump(el) {
    clearHL();
    el.classList.add("hl"); lastHL = el;
    if (window.PIDViewer && window.PIDViewer.focusBBox) {
      try { window.PIDViewer.focusBBox(el); } catch (e) { /* ignore */ }
    }
  }

  function run(q) {
    const box = document.getElementById("searchResults");
    box.innerHTML = "";
    q = (q || "").trim().toUpperCase();
    if (!q) return;
    const seen = new Set();
    const hits = entries.filter(e => {
      const up = e.text.toUpperCase();
      if (!up.includes(q)) return false;
      if (seen.has(up + "@" + Math.round(e.el.getBBox ? 0 : 0))) return false;
      return true;
    }).slice(0, 40);
    if (!hits.length) {
      box.innerHTML = '<div class="hit">No matches</div>';
      return;
    }
    hits.forEach(h => {
      const d = document.createElement("div");
      d.className = "hit"; d.textContent = h.text;
      d.addEventListener("click", () => jump(h.el));
      box.appendChild(d);
    });
    // auto-focus first hit
    jump(hits[0].el);
  }

  document.addEventListener("DOMContentLoaded", () => {
    const inp = document.getElementById("searchInput");
    const btn = document.getElementById("searchBtn");
    if (inp) {
      inp.addEventListener("input", () => run(inp.value));
      inp.addEventListener("keydown", e => { if (e.key === "Enter") run(inp.value); });
    }
    if (btn) btn.addEventListener("click", () => run(inp.value));
    const clr = document.getElementById("searchClear");
    if (clr) clr.addEventListener("click", () => {
      inp.value = ""; document.getElementById("searchResults").innerHTML = ""; clearHL();
    });
  });

  window.PIDSearch = { index, run };
})();
