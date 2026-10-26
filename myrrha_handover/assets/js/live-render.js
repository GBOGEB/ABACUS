// live-render.js — minimal markdown → HTML for live preview in slide-editor.html
// Mirrors master/render_all.py's md_to_html (kept intentionally small, no deps).

(function (global) {
  function escapeHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  function inline(s) {
    s = escapeHtml(s);
    s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/\*(.+?)\*/g, "<em>$1</em>");
    s = s.replace(/`(.+?)`/g, "<code>$1</code>");
    return s;
  }
  function mdToHtml(md) {
    const lines = md.split("\n");
    const out = [];
    let i = 0;
    while (i < lines.length) {
      const ln = lines[i];
      if (ln.startsWith("```")) {
        const code = [];
        i++;
        while (i < lines.length && !lines[i].startsWith("```")) { code.push(lines[i]); i++; }
        out.push('<pre class="ascii"><code>' + escapeHtml(code.join("\n")) + "</code></pre>");
        i++; continue;
      }
      const h = ln.match(/^(#{1,6}) (.*)$/);
      if (h) { out.push(`<h${h[1].length}>${inline(h[2])}</h${h[1].length}>`); i++; continue; }
      if (/^\s*[-*] /.test(ln)) {
        const items = [];
        while (i < lines.length && /^\s*[-*] /.test(lines[i])) {
          items.push(`<li>${inline(lines[i].replace(/^\s*[-*] /, ""))}</li>`); i++;
        }
        out.push("<ul>" + items.join("") + "</ul>"); continue;
      }
      if (/^\s*\d+\. /.test(ln)) {
        const items = [];
        while (i < lines.length && /^\s*\d+\. /.test(lines[i])) {
          items.push(`<li>${inline(lines[i].replace(/^\s*\d+\. /, ""))}</li>`); i++;
        }
        out.push("<ol>" + items.join("") + "</ol>"); continue;
      }
      if (ln.trim() === "") { i++; continue; }
      const para = [ln]; i++;
      while (i < lines.length && lines[i].trim() &&
             !/^(#{1,6} |```|\s*[-*] |\s*\d+\. )/.test(lines[i])) {
        para.push(lines[i]); i++;
      }
      out.push("<p>" + inline(para.join(" ")) + "</p>");
    }
    return out.join("\n");
  }
  global.LiveRender = { mdToHtml, inline, escapeHtml };
})(window);
