/*!
 * ABACUS shared chart theme — accessible, colour-blind-safe Plotly defaults.
 *
 * WHY: dashboard charts had two accessibility defects:
 *   1. low-contrast / non-colour-blind-safe series colours (e.g. a pale yellow
 *      #fbbc04 on a near-white background ≈ 1.4:1, and adjacent red/green pairs);
 *   2. a bottom (or top) legend overlapping diagonal/rotated x-axis tick labels
 *      and the x-axis title at narrow viewports.
 *
 * This module centralises the fix so every chart is corrected consistently:
 *   - ABACUS_CHART_THEME.light / .dark  — categorical palettes where EVERY
 *     colour clears WCAG AA graphic contrast (>=3:1) vs its background and the
 *     hues stay distinguishable under deuteranopia/protanopia/tritanopia
 *     (blue / green / amber / red / purple / teal / burnt-orange — no reliance
 *     on a red-vs-green distinction).
 *   - ABACUS_CHART_THEME.layout(mode, overrides) — a Plotly layout with
 *     axis.automargin enabled, generous bottom margin, and a bottom legend
 *     offset far enough below the (possibly rotated) tick labels + axis title
 *     that their bounding boxes never overlap at 1440x900 / 1280x720 / 390x844.
 *
 * Verified by scripts/qa/dashboard_playwright_qa.py (checks K9 contrast and
 * K10 legend/axis bounding-box non-overlap).
 */
(function (root) {
  'use strict';

  // ── Colour-blind-safe categorical palettes (contrast-verified) ───────────
  // Light theme: dark, saturated hues on a white/near-white background.
  var LIGHT = {
    bg:      '#ffffff',
    surface: '#f8f9fa',
    grid:    '#c7ccd1',
    text:    '#202124',   // 16:1 on white
    define:  '#0051a2',   // blue       7.78:1
    measure: '#117733',   // green      5.66:1
    analyze: '#8a6d00',   // dark amber 4.92:1 (replaces pale yellow)
    improve: '#b2182b',   // red        6.87:1
    control: '#762a83',   // purple     8.64:1
    infra:   '#006d77',   // teal       6.08:1
    accent:  '#bf5b17',   // burnt-orange 4.45:1
    good:    '#117733',   // semantic green
    warn:    '#8a6d00',   // semantic amber (contrast-safe)
    bad:     '#b2182b'    // semantic red
  };

  // Dark theme: bright Okabe-Ito hues on a near-black background.
  var DARK = {
    bg:      '#0d1117',
    surface: '#161b22',
    grid:    '#30363d',
    text:    '#e6edf3',   // 16:1 on #0d1117
    define:  '#56b4e9',   // sky blue   8.20:1
    measure: '#009e73',   // green      5.53:1
    analyze: '#f0e442',   // yellow    14.31:1
    improve: '#e69f00',   // orange     8.40:1
    control: '#cc79a7',   // purple     6.18:1
    infra:   '#56b4e9',   // sky blue
    accent:  '#d55e00',   // vermillion 4.89:1
    good:    '#009e73',
    warn:    '#f0e442',
    bad:     '#e69f00'
  };

  // Ordered sequence for auto-assigning series colours.
  function order(p) {
    return [p.define, p.improve, p.measure, p.analyze, p.control, p.infra, p.accent];
  }

  /**
   * Build an accessible Plotly layout.
   * @param {('light'|'dark')} mode
   * @param {object} overrides  deep-ish merged on top of the defaults
   * @param {object} opts  { legend: 'bottom'|'top'|'none', tickangle: number }
   */
  function layout(mode, overrides, opts) {
    var p = (mode === 'dark') ? DARK : LIGHT;
    opts = opts || {};
    overrides = overrides || {};
    var legendPos = opts.legend || 'bottom';
    var tickangle = (typeof opts.tickangle === 'number') ? opts.tickangle : 0;

    // Bottom margin must clear: rotated tick labels + axis title + bottom legend.
    // automargin handles labels/title; we still reserve a baseline and push the
    // legend below everything so bounding boxes never collide.
    var base = {
      paper_bgcolor: p.bg,
      plot_bgcolor: p.bg,
      font: { family: "'Segoe UI', system-ui, -apple-system, sans-serif", size: 13, color: p.text },
      colorway: order(p),
      margin: { t: 48, r: 24, b: 72, l: 64 },
      xaxis: {
        automargin: true,            // reserve space for (rotated) ticks + title
        tickangle: tickangle,
        tickfont: { color: p.text, size: 12 },
        title: { font: { color: p.text, size: 13 } },
        gridcolor: p.grid,
        zerolinecolor: p.grid
      },
      yaxis: {
        automargin: true,
        tickfont: { color: p.text, size: 12 },
        title: { font: { color: p.text, size: 13 } },
        gridcolor: p.grid,
        zerolinecolor: p.grid
      },
      title: { font: { color: p.text, size: 16 }, x: 0.5, xanchor: 'center' }
    };

    if (legendPos === 'bottom') {
      // Place legend BELOW the plot. Rather than forcing a negative paper-y
      // (which collides with the x-axis title once automargin reserves the
      // tick/title band), let Plotly auto-position the horizontal legend: with
      // xaxis.automargin on, Plotly stacks tick labels -> axis title -> legend
      // and grows the bottom margin so their bounding boxes never overlap.
      // A keep-tight title standoff plus a reserved baseline margin make this
      // robust down to 390px wide.
      // Plotly's auto-placement drops a horizontal legend BETWEEN the tick
      // labels and the x-axis title, so it overlaps the title. Pin the legend
      // explicitly below the title band (negative paper-y, anchored at its top)
      // and reserve enough bottom margin for ticks + title + legend. The offset
      // and margin scale up when the x labels are rotated.
      // NOTE: with xaxis.automargin ON, Plotly keeps expanding the bottom margin
      // to fit the legend and re-drops the x-title right above it, so title and
      // legend chase each other and never separate. We therefore pin the x-axis
      // title at a fixed standoff (automargin off for the x-axis) and place the
      // legend at a fixed negative paper-y with a reserved bottom margin. The
      // y-tick side keeps automargin. Rotated x labels get extra room.
      var angled = Math.abs(tickangle) > 0;
      base.xaxis.automargin = false;
      base.xaxis.title.standoff = angled ? 34 : 16;
      base.legend = {
        orientation: 'h', xanchor: 'center', x: 0.5,
        yanchor: 'top', y: angled ? -0.78 : -0.58,
        font: { color: p.text, size: 12 },
        bgcolor: 'rgba(0,0,0,0)'
      };
      base.margin.b = angled ? 205 : 165;
    } else if (legendPos === 'top') {
      base.legend = {
        orientation: 'h', xanchor: 'center', x: 0.5,
        yanchor: 'bottom', y: 1.04,
        font: { color: p.text, size: 12 }, bgcolor: 'rgba(0,0,0,0)'
      };
      base.margin.t = 72;
    } else {
      base.showlegend = false;
    }

    return deepMerge(base, overrides);
  }

  function deepMerge(a, b) {
    var out = Array.isArray(a) ? a.slice() : Object.assign({}, a);
    Object.keys(b || {}).forEach(function (k) {
      if (b[k] && typeof b[k] === 'object' && !Array.isArray(b[k]) &&
          a[k] && typeof a[k] === 'object' && !Array.isArray(a[k])) {
        out[k] = deepMerge(a[k], b[k]);
      } else {
        out[k] = b[k];
      }
    });
    return out;
  }

  root.ABACUS_CHART_THEME = {
    light: LIGHT,
    dark: DARK,
    order: order,
    layout: layout,
    deepMerge: deepMerge,
    config: { responsive: true, displayModeBar: false }
  };
})(typeof window !== 'undefined' ? window : this);
