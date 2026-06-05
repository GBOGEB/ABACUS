/* MINERVA CryoCell P&ID v4 - interactive viewer engine
 * Loads an SVG inline, exposes layer toggles, preset views, zoom/pan,
 * colour/mono + style switching, tag search and PNG export.
 * Layers are <g inkscape:groupmode="layer" id="NN_Name"> inside the SVG. */
(function () {
  "use strict";

  // ----- ordered layer list (must match the generator) -----
  const LAYERS = [
    "00_Background_TitleBlock", "01_Scope_Boundaries", "02_Structure_Reference",
    "03_Equipment_Vessels", "04A_Piping_PRIMARY_40K", "04B_Piping_BRANCHES_40K",
    "05A_Piping_PRIMARY_4p5K", "05B_Piping_BRANCHES_4p5K", "06A_Piping_PRIMARY_2K",
    "06B_Piping_BRANCHES_2K", "07_Piping_SECONDARY_Water", "08_Piping_OUTSIDE_SCOPE",
    "09_Valves_Mechanical", "08B_Valves_HORIZONTAL_OVERLAY", "10_Signals_Pneumatic",
    "11_Signals_Electric", "12_Signals_Hydraulic", "13_Instruments_Sensors",
    "14_Instruments_Control_DIS", "04C_Piping_LINENAMES", "02B_TerminalPoints_EDGE",
    "12_Tags_Instruments", "16_Legend_INTERACTIVE", "17_Notes_TOGGLEABLE"
  ];
  const HIDDEN_DEFAULT = new Set([
    "08B_Valves_HORIZONTAL_OVERLAY", "16_Legend_INTERACTIVE", "17_Notes_TOGGLEABLE"
  ]);
  // swatch colours for the checkbox panel (mono view greys these out)
  const SWATCH = {
    "04A_Piping_PRIMARY_40K": "#e00000", "04B_Piping_BRANCHES_40K": "#e00000",
    "05A_Piping_PRIMARY_4p5K": "#0033cc", "05B_Piping_BRANCHES_4p5K": "#0033cc",
    "06A_Piping_PRIMARY_2K": "#00a6bd", "06B_Piping_BRANCHES_2K": "#00a6bd",
    "07_Piping_SECONDARY_Water": "#00a000", "08_Piping_OUTSIDE_SCOPE": "#9a9a9a",
    "04C_Piping_LINENAMES": "#444444", "10_Signals_Pneumatic": "#7a00a0",
    "11_Signals_Electric": "#00529b", "12_Signals_Hydraulic": "#a06a00",
    "13_Instruments_Sensors": "#111", "02B_TerminalPoints_EDGE": "#0066a6",
    "09_Valves_Mechanical": "#222", "08B_Valves_HORIZONTAL_OVERLAY": "#888"
  };
  // grouped layout for the panel
  const GROUPS = [
    ["Frame & structure", ["00_Background_TitleBlock", "01_Scope_Boundaries",
      "02_Structure_Reference", "02B_TerminalPoints_EDGE", "03_Equipment_Vessels"]],
    ["Cryogenic piping", ["04A_Piping_PRIMARY_40K", "04B_Piping_BRANCHES_40K",
      "05A_Piping_PRIMARY_4p5K", "05B_Piping_BRANCHES_4p5K",
      "06A_Piping_PRIMARY_2K", "06B_Piping_BRANCHES_2K"]],
    ["Other piping & names", ["07_Piping_SECONDARY_Water", "08_Piping_OUTSIDE_SCOPE",
      "04C_Piping_LINENAMES"]],
    ["Valves", ["09_Valves_Mechanical", "08B_Valves_HORIZONTAL_OVERLAY"]],
    ["Signals", ["10_Signals_Pneumatic", "11_Signals_Electric", "12_Signals_Hydraulic"]],
    ["Instruments & tags", ["13_Instruments_Sensors", "14_Instruments_Control_DIS",
      "12_Tags_Instruments"]],
    ["Overlays", ["16_Legend_INTERACTIVE", "17_Notes_TOGGLEABLE"]]
  ];
  const VIEWS = {
    DEFAULT_FULL: LAYERS.filter(l => !HIDDEN_DEFAULT.has(l)),
    DEFAULT_PROCESS: ["00_Background_TitleBlock", "01_Scope_Boundaries",
      "02_Structure_Reference", "02B_TerminalPoints_EDGE", "03_Equipment_Vessels",
      "04A_Piping_PRIMARY_40K", "04B_Piping_BRANCHES_40K", "05A_Piping_PRIMARY_4p5K",
      "05B_Piping_BRANCHES_4p5K", "06A_Piping_PRIMARY_2K", "06B_Piping_BRANCHES_2K",
      "07_Piping_SECONDARY_Water", "08_Piping_OUTSIDE_SCOPE", "04C_Piping_LINENAMES",
      "09_Valves_Mechanical", "13_Instruments_Sensors", "12_Tags_Instruments"],
    DEFAULT_CONTROL: ["00_Background_TitleBlock", "01_Scope_Boundaries",
      "03_Equipment_Vessels", "08_Piping_OUTSIDE_SCOPE", "10_Signals_Pneumatic",
      "11_Signals_Electric", "12_Signals_Hydraulic", "13_Instruments_Sensors",
      "14_Instruments_Control_DIS", "12_Tags_Instruments"],
    DEFAULT_MAIN: ["00_Background_TitleBlock", "01_Scope_Boundaries",
      "03_Equipment_Vessels", "04A_Piping_PRIMARY_40K", "05A_Piping_PRIMARY_4p5K",
      "06A_Piping_PRIMARY_2K", "07_Piping_SECONDARY_Water", "09_Valves_Mechanical",
      "04C_Piping_LINENAMES", "02B_TerminalPoints_EDGE", "12_Tags_Instruments"],
    PRINT_MONO: LAYERS.filter(l => !HIDDEN_DEFAULT.has(l)).concat(["04C_Piping_LINENAMES"])
  };

  const state = { style: "STANDARD", mono: false, svg: null, scale: 1,
                  tx: 0, ty: 0, vb: null };
  const stage = document.getElementById("stage");
  const wrap = document.getElementById("canvasWrap");

  function fileFor() {
    const v = state.style + (state.mono ? "_MONO" : "");
    return `${window.SHEET.dir}/${window.SHEET.base}_${v}_v4.svg`;
  }

  function applyTransform() {
    if (!state.svg) return;
    state.svg.style.transform =
      `translate(${state.tx}px,${state.ty}px) scale(${state.scale})`;
  }

  function fitToStage() {
    if (!state.svg || !state.vb) return;
    const rw = stage.clientWidth - 40, rh = stage.clientHeight - 40;
    const s = Math.min(rw / state.vb.w, rh / state.vb.h);
    state.scale = s;
    state.tx = (stage.clientWidth - state.vb.w * s) / 2;
    state.ty = (stage.clientHeight - state.vb.h * s) / 2;
    applyTransform();
  }

  function setLayer(name, on) {
    if (!state.svg) return;
    const g = state.svg.querySelector(`[id="${CSS.escape(name)}"]`);
    if (g) g.style.display = on ? "inline" : "none";
  }

  function syncCheckboxesToSvg() {
    document.querySelectorAll("input.lyrchk").forEach(cb => {
      const g = state.svg.querySelector(`[id="${CSS.escape(cb.dataset.layer)}"]`);
      const on = g ? getComputedStyle(g).display !== "none" : false;
      cb.checked = on;
    });
  }

  function applyView(viewName) {
    const want = new Set(VIEWS[viewName] || VIEWS.DEFAULT_FULL);
    LAYERS.forEach(l => setLayer(l, want.has(l)));
    document.querySelectorAll("input.lyrchk").forEach(cb => {
      cb.checked = want.has(cb.dataset.layer);
    });
    document.querySelectorAll("[data-view]").forEach(b =>
      b.classList.toggle("active", b.dataset.view === viewName));
  }

  async function loadSvg(keepView) {
    const resp = await fetch(fileFor());
    const txt = await resp.text();
    const doc = new DOMParser().parseFromString(txt, "image/svg+xml");
    const svg = doc.documentElement;
    const vb = (svg.getAttribute("viewBox") || "0 0 1587 1122").split(/\s+/).map(Number);
    state.vb = { w: vb[2], h: vb[3] };
    svg.removeAttribute("width");
    svg.removeAttribute("height");
    wrap.innerHTML = "";
    wrap.appendChild(svg);
    state.svg = svg;
    // honour current checkbox state (or fit fresh)
    if (keepView) {
      document.querySelectorAll("input.lyrchk").forEach(cb =>
        setLayer(cb.dataset.layer, cb.checked));
    } else {
      syncCheckboxesToSvg();
      fitToStage();
    }
    applyTransform();
    if (window.PIDSearch) window.PIDSearch.index(svg);
  }

  // ---------- panel construction ----------
  function buildPanel() {
    const host = document.getElementById("layerPanel");
    GROUPS.forEach(([gname, items]) => {
      const g = document.createElement("div"); g.className = "group";
      const head = document.createElement("div"); head.className = "ghead";
      head.innerHTML = `<span>${gname}</span><span class="gtoggle">all / none</span>`;
      g.appendChild(head);
      const toggle = head.querySelector(".gtoggle");
      const boxes = [];
      items.forEach(l => {
        const lab = document.createElement("label");
        lab.className = "lyr" + (HIDDEN_DEFAULT.has(l) ? " hiddenDefault" : "");
        const cb = document.createElement("input");
        cb.type = "checkbox"; cb.className = "lyrchk"; cb.dataset.layer = l;
        cb.checked = !HIDDEN_DEFAULT.has(l);
        cb.addEventListener("change", () => setLayer(l, cb.checked));
        const sw = document.createElement("span"); sw.className = "sw";
        sw.style.background = SWATCH[l] || "transparent";
        const nm = document.createElement("span"); nm.className = "nm";
        nm.textContent = l.replace(/^\d+[A-Z]?_/, "").replace(/_/g, " ");
        lab.append(cb, sw, nm); g.appendChild(lab); boxes.push(cb);
      });
      toggle.addEventListener("click", () => {
        const anyOff = boxes.some(b => !b.checked);
        boxes.forEach(b => { b.checked = anyOff; setLayer(b.dataset.layer, anyOff); });
      });
      host.appendChild(g);
    });
  }

  // ---------- zoom / pan ----------
  function zoomAt(cx, cy, factor) {
    const ns = Math.min(40, Math.max(0.05, state.scale * factor));
    const k = ns / state.scale;
    state.tx = cx - (cx - state.tx) * k;
    state.ty = cy - (cy - state.ty) * k;
    state.scale = ns;
    applyTransform();
  }
  function wireZoomPan() {
    stage.addEventListener("wheel", e => {
      e.preventDefault();
      const r = stage.getBoundingClientRect();
      zoomAt(e.clientX - r.left, e.clientY - r.top, e.deltaY < 0 ? 1.12 : 1 / 1.12);
    }, { passive: false });
    let drag = null;
    wrap.addEventListener("mousedown", e => {
      drag = { x: e.clientX, y: e.clientY, tx: state.tx, ty: state.ty };
      wrap.classList.add("grabbing");
    });
    window.addEventListener("mousemove", e => {
      if (!drag) return;
      state.tx = drag.tx + (e.clientX - drag.x);
      state.ty = drag.ty + (e.clientY - drag.y);
      applyTransform();
    });
    window.addEventListener("mouseup", () => { drag = null; wrap.classList.remove("grabbing"); });
  }

  // ---------- PNG export ----------
  async function exportPng() {
    if (!state.svg) return;
    const clone = state.svg.cloneNode(true);
    clone.setAttribute("width", state.vb.w);
    clone.setAttribute("height", state.vb.h);
    const xml = new XMLSerializer().serializeToString(clone);
    const blob = new Blob([xml], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const img = new Image();
    await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = url; });
    const scale = 2.5;
    const cv = document.createElement("canvas");
    cv.width = state.vb.w * scale; cv.height = state.vb.h * scale;
    const ctx = cv.getContext("2d");
    ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, cv.width, cv.height);
    ctx.drawImage(img, 0, 0, cv.width, cv.height);
    URL.revokeObjectURL(url);
    const a = document.createElement("a");
    a.download = `${window.SHEET.base}_${state.style}${state.mono ? "_MONO" : ""}_v4.png`;
    a.href = cv.toDataURL("image/png");
    a.click();
  }

  // ---------- wire toolbar ----------
  function wireToolbar() {
    document.querySelectorAll("[data-view]").forEach(b =>
      b.addEventListener("click", () => applyView(b.dataset.view)));
    document.getElementById("btnMono").addEventListener("click", async e => {
      state.mono = !state.mono;
      e.target.classList.toggle("active", state.mono);
      e.target.textContent = state.mono ? "Mono: ON" : "Mono: OFF";
      await loadSvg(true);
    });
    document.querySelectorAll("[data-style]").forEach(b =>
      b.addEventListener("click", async () => {
        state.style = b.dataset.style;
        document.querySelectorAll("[data-style]").forEach(x =>
          x.classList.toggle("active", x === b));
        await loadSvg(true);
      }));
    document.getElementById("btnFit").addEventListener("click", fitToStage);
    document.getElementById("btnZin").addEventListener("click",
      () => zoomAt(stage.clientWidth / 2, stage.clientHeight / 2, 1.25));
    document.getElementById("btnZout").addEventListener("click",
      () => zoomAt(stage.clientWidth / 2, stage.clientHeight / 2, 1 / 1.25));
    document.getElementById("btnPng").addEventListener("click", exportPng);
  }

  window.addEventListener("resize", fitToStage);

  // ---------- boot ----------
  document.addEventListener("DOMContentLoaded", async () => {
    buildPanel();
    wireZoomPan();
    wireToolbar();
    document.querySelector('[data-style="STANDARD"]').classList.add("active");
    await loadSvg(false);
    window.PIDViewer = { applyView, loadSvg, focusBBox: (el) => {
      const bb = el.getBBox();
      const m = state.svg.querySelector("g") ? state.svg : state.svg;
      const ctm = el.getCTM();
      // map element centre into svg user space then to stage
      const cx = bb.x + bb.width / 2, cy = bb.y + bb.height / 2;
      const target = 3.0;
      state.scale = target;
      state.tx = stage.clientWidth / 2 - cx * target;
      state.ty = stage.clientHeight / 2 - cy * target;
      applyTransform();
    }};
  });
})();
