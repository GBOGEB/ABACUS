"""Public-safety scan: may this code go to a PUBLIC repo (ABACUS / DOW, gg_MATH)?

Fails on: private markers (project, people, organisation, private repo names), absolute user paths, secret-shaped strings,
and Python that only parses on 3.12+ (backslash or reused quote inside an f-string expression, PEP 701), because gg_MATH
declares 3.11. The private marker list comes from the private configuration (ESTATE_CONFIG); this file names nothing.

    python -I -X utf8 DMAIC_V3/binary_engines/public_safety_scan.py [files...]
"""

from __future__ import annotations

import collections
import io
import json
import re
import sys
import tokenize
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from estate_spec import CODE_DIR, CONFIG, CONFIG_IS_EXAMPLE, ESTATE  # noqa: E402

EST = ESTATE
# The marker list is private: it comes from the configuration, so this scanner names nothing itself.
_words = [str(w) for w in CONFIG.get("private_markers") or []]
MARKERS = (
    re.compile(r"(?i)\b(" + "|".join(_words) + r")\b")
    if _words
    else re.compile(r"(?!x)x")
)
USER_PATH = re.compile(
    r"(?i)[A-Z]:[\\/]+Users[\\/]+\w+|One"
    r"Drive -[ ]|C:[\\/]+DEV[\\/]+REPOS|C:[\\/]+repos[\\/]"
)  # split so it does not match itself
SECRET = re.compile(
    r"ghp_[A-Za-z0-9]{20,}|github_pat_\w{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
)


def fstring_312_only(src: str) -> list[int]:
    """Lines whose f-string replacement fields contain a backslash: valid on 3.12+, a SyntaxError on 3.11."""
    bad = []
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, SyntaxError):
        return bad
    for t in toks:
        name = tokenize.tok_name.get(t.type, "")
        if name == "FSTRING_MIDDLE":
            continue
        if name == "STRING" and re.match(r"(?i)^[rb]*f", t.string):
            body = t.string
            for field in re.findall(r"\{([^{}]*)\}", body):
                if "\\" in field:
                    bad.append(t.start[0])
    # 3.12 tokenizer splits f-strings: look at FSTRING_START..END spans for backslashes inside braces
    depth, line_has = 0, set()
    for t in toks:
        name = tokenize.tok_name.get(t.type, "")
        if name == "FSTRING_START":
            depth += 1
        elif name == "FSTRING_END":
            depth -= 1
        elif depth and name == "STRING" and "\\" in t.string:
            line_has.add(t.start[0])
        elif depth and name == "FSTRING_START" and depth > 1:
            line_has.add(t.start[0])
    return sorted(set(bad) | line_has)


def main() -> int:
    if CONFIG_IS_EXAMPLE:
        print(
            "WARNING: running on the example configuration: the private marker list is not loaded, so a clean result proves little"
        )
    files = [Path(f) for f in sys.argv[1:]] or sorted(
        p for p in CODE_DIR.iterdir() if p.suffix in (".py", ".ps1", ".yaml", ".md")
    )
    # estate_config.yaml is private by design and is never scanned for publication
    report, fail = [], False
    for f in files:
        s = f.read_text("utf-8")
        marks = collections.Counter(m.group(1).upper() for m in MARKERS.finditer(s))
        paths = len(USER_PATH.findall(s))
        secrets = len(SECRET.findall(s))
        f312 = fstring_312_only(s) if f.suffix == ".py" else []
        ok = not marks and not paths and not secrets and not f312
        fail |= not ok
        report.append(
            {
                "file": f.name,
                "public_ok": ok,
                "private_markers": sum(marks.values()),
                "top": dict(marks.most_common(5)),
                "user_paths": paths,
                "secrets": secrets,
                "py312_only_lines": f312[:10],
            }
        )
        print(
            f"{'OK  ' if ok else 'HOLD'} {f.name:28} markers={sum(marks.values()):4} paths={paths:2} py312-only={f312[:6]} {dict(marks.most_common(4))}"
        )
    (EST / "deep").mkdir(parents=True, exist_ok=True)
    (EST / "deep" / "PUBLIC_SAFETY.json").write_text(
        json.dumps(report, indent=1), "utf-8"
    )
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
