#!/usr/bin/env python3
"""Generate the ABACUS repository map (docs/repo-structure/index.html).

    python tools/root_refactor/discovery_page.py --write   # regenerate the page
    python tools/root_refactor/discovery_page.py --check   # exit 1 if the committed page is stale
    python tools/root_refactor/discovery_page.py           # one-line summary

A human entry page: where everything is and how to open it, on GitHub, on
GitHub Pages and in a local checkout through Windows File Explorer. It is
rendered from two sources of truth so it never drifts:

* docs/repo-structure/ROOT_INVENTORY.csv   (every file at the root at the inventory commit)
* docs_versioned/ROOT_RELOCATION_MAP.csv   (every file moved off the root so far)

Output is deterministic (no timestamps), self-contained (inline CSS and JS,
no external fetches) and works from disk (file://) and from GitHub Pages.
"""
from __future__ import annotations

import argparse
import csv
import html
import importlib.util
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = "docs/repo-structure/index.html"
INVENTORY = "docs/repo-structure/ROOT_INVENTORY.csv"
REGEN = "python tools/root_refactor/discovery_page.py --write"

REPO = "https://github.com/GBOGEB/ABACUS"
TREE = REPO + "/tree/main"
BLOB = REPO + "/blob/main"
PAGES = "https://gbogeb.github.io/ABACUS/"
PAGE = PAGES + "repo-structure/"
CLONE = REPO + ".git"
FAMILY_ORDER = ["KEEP", "F1", "F2", "F3", "F4", "F5"]

# (path, is_folder, purpose)
START_HERE = [
    ("README.md", False, "Front door: what ABACUS is and how to run it."),
    ("docs/index.html", False, "GitHub Pages site (docs/ is the Pages source)."),
    (
        ".jade/repo.yaml",
        False,
        "JADE pointer: repo identity for the governance tooling.",
    ),
    ("DMAIC_V3", True, "Runtime package: the DMAIC V3 engine."),
    ("tests", True, "Test suite (pytest / unittest)."),
    (".github/workflows", True, "CI workflows and gates."),
    ("docs_versioned", True, "Frozen history: relocated reports and versioned docs."),
    (
        "docs/repo-structure/ROOT_REFACTOR_PLAN.md",
        False,
        "Root refactor plan: families, waves, rules.",
    ),
]


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


inventory_mod = _load("root_inventory", "inventory.py")
relocate_mod = _load("root_relocate", "relocate.py")
FAMILY_NAMES: dict[str, str] = inventory_mod.FAMILY_NAMES


def load_inventory(root: Path = ROOT) -> list[dict]:
    with (root / INVENTORY).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def url_path(path: str) -> str:
    return quote(path, safe="/._-~()")


def gh_url(path: str, folder: bool = False) -> str:
    return (TREE if folder else BLOB) + "/" + url_path(path)


def rel_href(path: str, folder: bool = False) -> str:
    """Relative link from docs/repo-structure/ to a repo path (works on file://)."""
    return "../../" + url_path(path) + ("/" if folder else "")


def merge(inv: list[dict], moves: list[dict]) -> list[dict]:
    by_old = {m["old_path"]: m for m in moves}
    rows = []
    seen = set()
    for r in inv:
        m = by_old.get(r["path"])
        seen.add(r["path"])
        if m:
            status, now = "MOVED", m["new_path"]
        elif r["family"] == "KEEP":
            status, now = "STAYS", r["path"]
        else:
            status, now = "AT ROOT", r["path"]
        rows.append(
            {
                "name": r["path"],
                "family": r["family"],
                "wave": r["wave"] or (m or {}).get("wave", ""),
                "status": status,
                "now": now,
                "prune": r.get("prune_candidate", ""),
            }
        )
    for (
        m
    ) in moves:  # map rows not in the inventory (should not happen; never hide them)
        if m["old_path"] not in seen:
            rows.append(
                {
                    "name": m["old_path"],
                    "family": m["family"],
                    "wave": m["wave"],
                    "status": "MOVED",
                    "now": m["new_path"],
                    "prune": "",
                }
            )
    rows.sort(key=lambda x: (x["name"].lower(), x["name"]))
    return rows


def family_stats(inv: list[dict], moves: list[dict]) -> list[dict]:
    fams = FAMILY_ORDER + sorted({r["family"] for r in inv} - set(FAMILY_ORDER))
    out = []
    for fam in fams:
        rs = [r for r in inv if r["family"] == fam]
        moved = sum(1 for m in moves if m["family"] == fam)
        waves = sorted({r["wave"] for r in rs if r["wave"]})
        out.append(
            {
                "family": fam,
                "name": FAMILY_NAMES.get(fam, ""),
                "total": len(rs),
                "moved": moved,
                "remaining": max(len(rs) - moved, 0),
                "wave": ", ".join(waves) or "-",
            }
        )
    return out


def copy_btn(text: str, label: str = "Copy") -> str:
    return f'<button type="button" class="copy" data-copy="{esc(text)}">{esc(label)}</button>'


def local_link(path: str, folder: bool = False) -> str:
    return (
        f'<a class="local" data-p="{esc(path)}" data-dir="{1 if folder else 0}" '
        f'href="{esc(rel_href(path, folder))}">Local</a>'
    )


CSS = """
:root{--bg:#fbfbfa;--fg:#1d2228;--muted:#5d6670;--card:#ffffff;--line:#dde1e5;--accent:#0b6bcb;
--accent-weak:#e3effb;--chip:#eef1f4;--ok:#1d7a46;--warn:#8a5a00;--focus:#0b6bcb}
@media (prefers-color-scheme: dark){:root{--bg:#14171a;--fg:#e6e9ec;--muted:#a1aab3;--card:#1c2024;
--line:#30363c;--accent:#5aa9f0;--accent-weak:#16304a;--chip:#262b31;--ok:#5cc58b;--warn:#e0b45a;--focus:#8cc4f7}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",
Roboto,"Helvetica Neue",Arial,sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 40px}
h1{font-size:1.7rem;margin:0 0 8px}h2{font-size:1.2rem;margin:32px 0 12px}h3{font-size:1rem;margin:0 0 6px}
p{margin:0 0 10px}a{color:var(--accent)}
a:focus-visible,button:focus-visible,input:focus-visible{outline:3px solid var(--focus);outline-offset:2px}
code{font-family:Consolas,"SFMono-Regular",Menlo,monospace;font-size:.88em;overflow-wrap:anywhere}
.muted{color:var(--muted)}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 16px}
.ways{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
.cmd{display:flex;gap:8px;align-items:flex-start;margin:6px 0}.cmd code{flex:1;min-width:0;padding:4px 6px;
background:var(--chip);border-radius:4px}
button{font:inherit;font-size:.85rem;color:var(--fg);background:var(--chip);border:1px solid var(--line);
border-radius:6px;padding:3px 9px;cursor:pointer}button:hover{border-color:var(--accent)}
button[aria-pressed=true]{background:var(--accent);border-color:var(--accent);color:#fff}
label{font-weight:600;display:block;margin:4px 0}
input[type=text],input[type=search]{font:inherit;width:100%;padding:6px 8px;border:1px solid var(--line);
border-radius:6px;background:var(--bg);color:var(--fg)}
.grid{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}
.grid .card p{color:var(--muted);font-size:.92rem}.links a{margin-right:12px}
.fam{display:grid;grid-template-columns:4.5em 1fr;gap:4px 12px;padding:10px 0;border-top:1px solid var(--line)}
.fam:first-of-type{border-top:0}.fam .nums{grid-column:2;font-size:.9rem;color:var(--muted)}
.bar{grid-column:2;height:8px;background:var(--chip);border-radius:4px;overflow:hidden}
.bar span{display:block;height:100%;background:var(--accent)}
.filters{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:10px 0}
.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:var(--card)}
table{border-collapse:collapse;width:100%;font-size:.88rem}
th,td{text-align:left;padding:5px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{position:sticky;top:0;background:var(--card)}td.n{overflow-wrap:anywhere;min-width:12em}
td.now{overflow-wrap:anywhere;min-width:14em}
.st{font-size:.75rem;font-weight:600;white-space:nowrap}.st-MOVED{color:var(--ok)}.st-STAYS{color:var(--muted)}
.st-AT{color:var(--warn)}
.badge{display:inline-block;font-size:.72rem;color:var(--muted);background:var(--chip);border-radius:4px;
padding:0 5px;margin-top:2px;overflow-wrap:anywhere}
.sel{border:0;background:none;padding:0 4px;color:var(--accent)}
footer{margin-top:36px;font-size:.85rem;color:var(--muted)}
#status{min-height:1.4em;font-size:.85rem;color:var(--ok)}
"""

JS = r"""
(function(){
var KEY='abacus.localRoot';
function get(){try{return localStorage.getItem(KEY)||'';}catch(e){return '';}}
function put(v){try{if(v){localStorage.setItem(KEY,v);}else{localStorage.removeItem(KEY);}}catch(e){}}
var status=document.getElementById('status');
function say(t){if(status){status.textContent=t;}}
function copy(t){
  function fallback(){var a=document.createElement('textarea');a.value=t;document.body.appendChild(a);a.select();
    try{document.execCommand('copy');say('Copied: '+t);}catch(e){say('Copy failed; select the text manually.');}
    document.body.removeChild(a);}
  if(navigator.clipboard&&navigator.clipboard.writeText){
    navigator.clipboard.writeText(t).then(function(){say('Copied: '+t);},fallback);}else{fallback();}
}
function clean(v){v=(v||'').trim().replace(/^"|"$/g,'');return v.replace(/[\\\/]+$/,'');}
function fileUrl(root,p,dir){
  var full=root.replace(/\\/g,'/')+'/'+p+(dir?'/':'');
  if(full.charAt(0)!=='/'){full='/'+full;}
  return 'file://'+encodeURI(full).replace(/#/g,'%23').replace(/\?/g,'%3F');
}
var input=document.getElementById('localroot');
var isWeb=location.protocol.indexOf('http')===0;
function apply(){
  var root=clean(input.value);
  var links=document.querySelectorAll('a.local');
  for(var i=0;i<links.length;i++){
    var a=links[i],p=a.getAttribute('data-p'),dir=a.getAttribute('data-dir')==='1';
    if(!a.getAttribute('data-rel')){a.setAttribute('data-rel',a.getAttribute('href'));}
    if(root){a.setAttribute('href',fileUrl(root,p,dir));a.removeAttribute('title');}
    else if(isWeb){a.setAttribute('href','#open');a.setAttribute('title','Set your local ABACUS folder first');}
    else{a.setAttribute('href',a.getAttribute('data-rel'));}
  }
  var box=document.getElementById('localcmds');
  if(root){
    box.hidden=false;
    document.getElementById('cmd-open').textContent='explorer.exe "'+root+'"';
  }else{box.hidden=true;}
}
input.value=get();
input.addEventListener('input',function(){put(clean(input.value));apply();});
apply();
document.addEventListener('click',function(ev){
  var b=ev.target.closest?ev.target.closest('button'):null;if(!b){return;}
  if(b.hasAttribute('data-copy')){copy(b.getAttribute('data-copy'));return;}
  if(b.hasAttribute('data-copyof')){copy(document.getElementById(b.getAttribute('data-copyof')).textContent);return;}
  if(b.hasAttribute('data-sel')){
    var root=clean(input.value);
    if(!root){say('Set "Your local ABACUS folder" first.');input.focus();return;}
    copy('explorer.exe /select,"'+root+'\\'+b.getAttribute('data-sel').replace(/\//g,'\\')+'"');return;}
});
var q=document.getElementById('q'),moved=document.getElementById('movedonly');
var chips=document.querySelectorAll('button[data-fam]');
var rows=document.querySelectorAll('#files tbody tr');
var count=document.getElementById('count');
function filter(){
  var s=q.value.trim().toLowerCase(),on={},any=false,n=0;
  for(var i=0;i<chips.length;i++){if(chips[i].getAttribute('aria-pressed')==='true'){on[chips[i].getAttribute('data-fam')]=1;any=true;}}
  var mo=moved.getAttribute('aria-pressed')==='true';
  for(var j=0;j<rows.length;j++){
    var r=rows[j],ok=true;
    if(s&&r.getAttribute('data-s').indexOf(s)<0){ok=false;}
    if(any&&!on[r.getAttribute('data-f')]){ok=false;}
    if(mo&&r.getAttribute('data-m')!=='1'){ok=false;}
    r.hidden=!ok;if(ok){n++;}
  }
  count.textContent=n+' of '+rows.length+' files shown';
}
function toggle(b){b.setAttribute('aria-pressed',b.getAttribute('aria-pressed')==='true'?'false':'true');filter();}
for(var k=0;k<chips.length;k++){chips[k].addEventListener('click',function(){toggle(this);});}
moved.addEventListener('click',function(){toggle(this);});
q.addEventListener('input',filter);
document.getElementById('filters').hidden=false;
filter();
})();
"""


def render(root: Path = ROOT) -> str:
    inv = load_inventory(root)
    moves = relocate_mod.load_map(root)
    rows = merge(inv, moves)
    stats = family_stats(inv, moves)
    commit = (inv[0]["observed_commit"] if inv else "")[:10]
    total, nmoved = len(inv), len(moves)

    o: list[str] = []
    w = o.append
    w("<!DOCTYPE html>")
    w('<html lang="en">')
    w("<head>")
    w('<meta charset="utf-8">')
    w('<meta name="viewport" content="width=device-width, initial-scale=1">')
    w("<title>ABACUS repository map</title>")
    w(
        '<meta name="description" content="Where everything is in the ABACUS repository and how to open it.">'
    )
    w("<style>" + CSS.strip() + "</style>")
    w("</head>")
    w("<body>")
    w("<main>")
    w("<h1>ABACUS \u2014 repository map</h1>")
    w(
        "<p>Where everything in the ABACUS repository lives, and how to open it on GitHub, on GitHub Pages "
        "or in your own checkout with Windows File Explorer. This page is generated from two sources of truth, "
        '<a href="ROOT_INVENTORY.csv">ROOT_INVENTORY.csv</a> (every file at the repository root when the '
        'inventory was taken) and <a href="../../docs_versioned/ROOT_RELOCATION_MAP.csv">ROOT_RELOCATION_MAP.csv</a> '
        f'(every file moved off the root so far; <a href="{BLOB}/docs_versioned/ROOT_RELOCATION_MAP.csv">on GitHub</a>), '
        'so it follows the <a href="ROOT_REFACTOR_PLAN.md">root refactor plan</a> without drifting.</p>'
    )

    # 2. How to open it
    w('<h2 id="open">How to open it</h2>')
    w('<div class="ways">')
    w('<section class="card"><h3>GitHub</h3>')
    for u in (REPO, TREE):
        w(f'<div class="cmd"><code><a href="{u}">{u}</a></code>{copy_btn(u)}</div>')
    w("</section>")
    w('<section class="card"><h3>GitHub Pages</h3>')
    for u in (PAGES, PAGE):
        w(f'<div class="cmd"><code><a href="{u}">{u}</a></code>{copy_btn(u)}</div>')
    w("</section>")
    w('<section class="card"><h3>Local (Windows File Explorer)</h3>')
    w('<label for="localroot">Your local ABACUS folder</label>')
    w(
        '<input type="text" id="localroot" placeholder="C:\\path\\to\\ABACUS" autocomplete="off" spellcheck="false">'
    )
    w(
        '<p class="muted">Saved in this browser only. Once set, every <em>Local</em> link on this page opens '
        "that file, and the copy buttons give you File Explorer commands.</p>"
    )
    w('<div id="localcmds" hidden>')
    w(
        '<div class="cmd"><code id="cmd-open"></code><button type="button" class="copy" '
        'data-copyof="cmd-open">Copy</button></div>'
    )
    w(
        '<p class="muted">Per file: the <strong>\u29c9</strong> button in the table copies '
        '<code>explorer.exe /select,"&lt;folder&gt;\\&lt;path&gt;"</code> (paste it in PowerShell).</p>'
    )
    w("</div>")
    w(
        f'<div class="cmd"><code>git clone {CLONE}</code>{copy_btn("git clone " + CLONE)}</div>'
    )
    w(
        '<p class="muted">Browsers may block <code>file:///</code> links from an https page; the copied '
        "PowerShell command is the reliable route. From a locally opened copy of this page the links work.</p>"
    )
    w("</section>")
    w("</div>")
    w('<p id="status" role="status" aria-live="polite"></p>')

    # 3. Start here
    w('<h2 id="start">Start here</h2>')
    w('<div class="grid">')
    for path, folder, purpose in START_HERE:
        shown = path + ("/" if folder else "")
        w(
            f'<section class="card"><h3><code>{esc(shown)}</code></h3><p>{esc(purpose)}</p>'
            f'<div class="links"><a href="{esc(gh_url(path, folder))}">GitHub</a>{local_link(path, folder)}</div>'
            "</section>"
        )
    w("</div>")

    # 4. Progress
    w('<h2 id="progress">Root refactor progress</h2>')
    w(
        f"<p>Root files at inventory commit: <strong>{total}</strong> \u00b7 moved so far: "
        f"<strong>{nmoved}</strong> \u00b7 root files now: <strong>{max(total - nmoved, 0)}</strong></p>"
    )
    w('<div class="card">')
    for s in stats:
        pct = 0 if not s["total"] else round(100 * s["moved"] / s["total"])
        stays = s["family"] == "KEEP"
        nums = (
            f'{s["total"]} files \u00b7 stay at root'
            if stays
            else f'{s["total"]} files \u00b7 moved {s["moved"]} \u00b7 remaining {s["remaining"]} '
            f'\u00b7 wave {esc(s["wave"])} \u00b7 {pct}%'
        )
        w(
            f'<div class="fam"><strong>{esc(s["family"])}</strong><span>{esc(s["name"])}</span>'
            f'<span class="nums">{nums}</span>'
            f'<div class="bar" role="img" aria-label="{esc(s["family"])} {pct}% moved"><span style="width:{pct}%">'
            "</span></div></div>"
        )
    w("</div>")

    # 5. Find a file
    w('<h2 id="find">Find a file</h2>')
    w('<div id="filters" class="filters" hidden>')
    w(
        '<div style="flex:1 1 220px"><label for="q">Search name or location</label>'
        '<input type="search" id="q" placeholder="e.g. HANDOVER or generated_reports" autocomplete="off"></div>'
    )
    w('<div role="group" aria-label="Filter by family">')
    for fam in [s["family"] for s in stats]:
        w(
            f'<button type="button" data-fam="{esc(fam)}" aria-pressed="false" '
            f'title="{esc(FAMILY_NAMES.get(fam, ""))}">{esc(fam)}</button>'
        )
    w("</div>")
    w('<button type="button" id="movedonly" aria-pressed="false">Moved only</button>')
    w("</div>")
    w(f'<p id="count" class="muted">{len(rows)} files</p>')
    w('<div class="tablewrap"><table id="files">')
    w(
        "<thead><tr><th>Name</th><th>Family</th><th>Wave</th><th>Status</th><th>Location now</th>"
        "<th>Open</th></tr></thead>"
    )
    w("<tbody>")
    for r in rows:
        name, now = r["name"], r["now"]
        search = esc((name + " " + now).lower())
        st = r["status"]
        badge = (
            f'<br><span class="badge">{esc(r["prune"])}</span>' if r["prune"] else ""
        )
        w(
            f'<tr data-s="{search}" data-f="{esc(r["family"])}" data-m="{1 if st == "MOVED" else 0}">'
            f'<td class="n">{esc(name)}{badge}</td><td>{esc(r["family"])}</td><td>{esc(r["wave"])}</td>'
            f'<td><span class="st st-{st.split()[0]}">{st}</span></td><td class="now">{esc(now)}</td>'
            f'<td class="links"><a href="{esc(gh_url(now))}">GitHub</a>{local_link(now)}'
            f'<button type="button" class="sel" data-sel="{esc(now)}" '
            f'aria-label="Copy File Explorer command for {esc(now)}" title="Copy explorer /select command">'
            "\u29c9</button></td></tr>"
        )
    w("</tbody></table></div>")

    # 6. Footer
    w("<footer>")
    w(
        f"<p>Generated by <code>{REGEN}</code> from the inventory observed at commit "
        f"<code>{esc(commit)}</code> and the relocation map as committed. This is not live state: "
        "regenerate after each wave.</p>"
    )
    w("</footer>")
    w("</main>")
    w("<script>" + JS.strip() + "</script>")
    w("</body>")
    w("</html>")
    return "\n".join(o) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--write", action="store_true", help=f"write {OUT}")
    g.add_argument("--check", action="store_true", help=f"exit 1 if {OUT} is stale")
    args = ap.parse_args(argv)
    page = render()
    out = ROOT / OUT
    if args.write:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(page.encode("utf-8"))
        print(f"wrote {OUT} ({len(page.encode('utf-8'))} bytes)")
        return 0
    if args.check:
        current = out.read_bytes().decode("utf-8") if out.exists() else ""
        if current != page:
            print(f"{OUT} is stale; regenerate with: {REGEN}", file=sys.stderr)
            return 1
        print(f"{OUT} is up to date")
        return 0
    inv = load_inventory()
    moved = len(relocate_mod.load_map())
    print(
        f"repository map: {len(inv)} root files at inventory, {moved} moved, "
        f"{len(inv) - moved} at root now; {len(merge(inv, relocate_mod.load_map()))} table rows"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
