#!/usr/bin/env python3
"""Python interpreter-version SSOT for ABACUS CI.

Authority : ssot/python_versions.yaml (human-maintained, AUTHORITATIVE)
Derived   : every setup-python version in .github/workflows/*.yml and
            .github/actions/*/action.yml, plus ssot `derived_files`.

    python tools/ci/python_versions.py report   # list every version site
    python tools/ci/python_versions.py check    # exit 1 on drift (CI guard)
    python tools/ci/python_versions.py sync     # rewrite derived files

`sync` is idempotent and only ever rewrites the text span of a version value,
so YAML layout, comments and SHA pins are preserved byte-for-byte.
Mapping rules are documented in ssot/python_versions.yaml.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SSOT_PATH = Path("ssot/python_versions.yaml")
LANES_VIEW_PATH = Path("ssot/python_versions.lanes.json")
LANE_DECL_RE = re.compile(r"^\s*PYTHON_LANE:\s*['\"]?([A-Za-z0-9_-]+)['\"]?\s*$", re.M)
STRAY_RE = re.compile(r"""python[-_]version\\?["']?\s*[:=]\s*\\?["']?(3\.\d{1,2})""", re.I)
COND_RE = re.compile(r"matrix\.([A-Za-z0-9_-]+)\s*(==|!=)\s*(['\"])(3\.\d{1,2})\3")
WORKFLOW_GLOBS = (".github/workflows/*.yml", ".github/workflows/*.yaml",
                  ".github/actions/*/action.yml", ".github/actions/*/action.yaml")

VERSION_RE = re.compile(r"^3\.\d{1,2}$")
LITERAL_RE = re.compile(r"""(?<![\d.])3\.\d{1,2}(?![\d.])""")
JSON_LIST_RE = re.compile(r'\[\s*"3\.\d{1,2}"(?:\s*,\s*"3\.\d{1,2}")*\s*\]')
REF_RE = re.compile(r"^\$\{\{\s*(matrix|env|inputs)\.([A-Za-z0-9_-]+)\s*\}\}$")


def vkey(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


class SyncError(RuntimeError):
    """A version site the rules cannot rewrite safely."""


# --------------------------------------------------------------------------- policy


@dataclass
class Lane:
    versions: list[str]
    pin: str
    cap: str | None = None

    @property
    def name(self) -> str:
        return self.cap or "default"

    @property
    def midpoint(self) -> str:
        return self.versions[len(self.versions) // 2]

    def view(self) -> dict:
        return {"versions": list(self.versions), "pin": self.pin, "oldest": self.versions[0],
                "midpoint": self.midpoint, "newest": self.versions[-1]}

    def role_map(self, old: list[str]) -> dict[str, str]:
        """old matrix value -> new value, for rewriting `matrix.K == 'X'` conditions."""
        distinct = sorted(set(old), key=vkey)
        if len(distinct) == 1:
            return {distinct[0]: self.pin}
        mapping = {v: self.midpoint for v in distinct[1:-1]}
        mapping[distinct[0]] = self.versions[0]
        mapping[distinct[-1]] = self.versions[-1]
        return mapping

    def for_list(self, count: int) -> list[str]:
        if count >= 3:
            return list(self.versions)
        if count == 2:
            return [self.versions[0], self.versions[-1]]
        return [self.pin]

    def for_roles(self, old: list[str]) -> dict[str, str]:
        distinct = sorted(set(old), key=vkey)
        if len(distinct) == 1:
            return {distinct[0]: self.pin}
        if len(distinct) == 2:
            return {distinct[0]: self.versions[0], distinct[1]: self.versions[-1]}
        if len(distinct) == 3 and len(self.versions) >= 3:
            return {
                distinct[0]: self.versions[0],
                distinct[1]: self.versions[len(self.versions) // 2],
                distinct[2]: self.versions[-1],
            }
        if len(distinct) == 3 and len(self.versions) == 2:
            # Lane too narrow for three roles: the middle cell folds into the
            # oldest; identical include entries are then removed by the scanner.
            return {distinct[0]: self.versions[0], distinct[1]: self.versions[0],
                    distinct[2]: self.versions[-1]}
        raise SyncError(f"include/exclude uses {len(distinct)} versions {distinct}; migrate by hand")


@dataclass
class Policy:
    supported: list[str]
    default: str
    experimental: list[str]
    canary: set[str]
    caps: dict[str, dict]
    derived: list[dict]
    end_of_life: list[str] = field(default_factory=list)
    held: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, root: Path) -> "Policy":
        data = yaml.safe_load((root / SSOT_PATH).read_text(encoding="utf-8"))
        supported = sorted(data["supported"], key=vkey)
        if data["default"] not in supported:
            raise SyncError("default must be one of supported")
        for name, cap in data.get("caps", {}).items():
            if cap["max"] not in supported:
                raise SyncError(f"cap {name}: max must be one of supported")
        return cls(supported, data["default"], list(data.get("experimental", [])),
                   set(data.get("canary_workflows", [])), data.get("caps", {}),
                   data.get("derived_files", []), list(data.get("end_of_life", [])),
                   {k: " ".join(str(v).split()) for k, v in (data.get("held_workflows") or {}).items()})

    def lane(self, rel: str, text: str, job: str | None = None) -> Lane:
        if rel in self.canary:
            return Lane(list(self.experimental), self.experimental[0], "experimental")
        cap, cap_name = None, None
        for name, spec in self.caps.items():
            if job is not None and f"{rel}:{job}" in spec.get("exempt_jobs", []):
                continue  # named job that does not use what this cap protects
            if any(re.search(p, text) for p in spec["patterns"]):
                if cap is None or vkey(spec["max"]) < vkey(cap):
                    cap, cap_name = spec["max"], name
        return self.capped_lane(cap_name)

    def role_value(self, role: str) -> str:
        return {"default": self.default, "oldest": self.supported[0],
                "newest": self.supported[-1]}[role]

    def capped_lane(self, cap_name: str | None) -> Lane:
        cap = self.caps[cap_name]["max"] if cap_name else None
        versions = [v for v in self.supported if cap is None or vkey(v) <= vkey(cap)]
        pin = self.default if vkey(self.default) <= vkey(versions[-1]) else versions[-1]
        return Lane(versions, pin, cap_name)

    def lanes_view(self) -> str:
        """JSON materialized view for consumers that cannot parse YAML (bash/jq, stdlib-only scripts)."""
        lanes = {"default": self.capped_lane(None).view()}
        for name, spec in self.caps.items():
            lanes[name] = {**self.capped_lane(name).view(), "reason": " ".join(spec["reason"].split())}
        view = {
            "schema": "abacus-python-lanes/1.0.0",
            "authority": SSOT_PATH.as_posix(),
            "authority_state": "MATERIALIZED_VIEW",
            "generated_by": "tools/ci/python_versions.py sync",
            "supported": self.supported,
            "default": self.default,
            "experimental": self.experimental,
            "lanes": lanes,
        }
        return json.dumps(view, indent=2) + "\n"


# --------------------------------------------------------------------------- scanning


@dataclass
class Site:
    kind: str          # pin | list | roles | expr
    line: int
    old: str
    new: str
    start: int
    end: int
    where: str


@dataclass
class FileScan:
    rel: str
    text: str
    lane: Lane
    sites: list[Site] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    def synced_text(self) -> str:
        out = self.text
        seen: set[tuple[int, int]] = set()
        for site in sorted(self.sites, key=lambda s: s.start, reverse=True):
            if (site.start, site.end) in seen:
                continue
            seen.add((site.start, site.end))
            out = out[:site.start] + site.new + out[site.end:]
        return out


def mget(node, key):
    if isinstance(node, yaml.MappingNode):
        for k, v in node.value:
            if isinstance(k, yaml.ScalarNode) and k.value == key:
                return v
    return None


def items(node):
    return node.value if isinstance(node, yaml.SequenceNode) else []


def quote(node: yaml.ScalarNode) -> str:
    return node.style if node.style in ("'", '"') else "'"


class Scanner:
    def __init__(self, scan: FileScan, policy: Policy):
        self.s = scan
        self.policy = policy
        self.lane = scan.lane  # narrowed per job in run()

    # -- site recorders ------------------------------------------------------
    def add(self, kind, node, new, where):
        self.add_span(kind, node.start_mark.index, node.end_mark.index, new, where)

    def add_span(self, kind, start, end, new, where):
        old = self.s.text[start:end]
        line = self.s.text.count("\n", 0, start) + 1
        self.s.sites.append(Site(kind, line, old, new, start, end, where))

    def pin(self, node: yaml.ScalarNode, where: str) -> str:
        q = quote(node)
        self.add("pin", node, f"{q}{self.lane.pin}{q}", where)
        return node.value.strip()

    def relabel(self, name_node, old: str, new: str, where: str):
        """Keep human labels such as 'Setup Python 3.12' in step with the pin."""
        if not isinstance(name_node, yaml.ScalarNode) or old == new:
            return
        start = name_node.start_mark.index
        span = self.s.text[start:name_node.end_mark.index]
        for m in LITERAL_RE.finditer(span):
            if m.group(0) == old:
                self.add_span("label", start + m.start(), start + m.end(), new, where)

    def conditions(self, node, maps: dict[str, dict[str, str]], where: str):
        """Rewrite `matrix.K == 'X'` so a condition keeps selecting the same matrix role."""
        if not isinstance(node, yaml.ScalarNode):
            return
        start = node.start_mark.index
        span = self.s.text[start:node.end_mark.index]
        for m in COND_RE.finditer(span):
            key, version = m.group(1), m.group(4)
            if key not in maps:
                self.s.problems.append(f"{where}: condition on matrix.{key} == {version!r} "
                                       "but that matrix is not a literal list; compare to a job output instead")
                continue
            if version not in maps[key]:
                self.s.problems.append(f"{where}: condition matrix.{key} == {version!r} matches no matrix cell")
                continue
            self.add_span("cond", start + m.start(4), start + m.end(4), maps[key][version], where)

    def flow_list(self, node: yaml.SequenceNode, where: str):
        scalars = node.value
        if not node.flow_style or not scalars:
            self.s.problems.append(f"{where}: block-style or empty version list")
            return
        if not all(isinstance(n, yaml.ScalarNode) and VERSION_RE.match(n.value) for n in scalars):
            self.s.problems.append(f"{where}: non-version entry in python matrix")
            return
        text = self.s.text
        lead = text[node.start_mark.index + 1:scalars[0].start_mark.index]
        trail = text[scalars[-1].end_mark.index:node.end_mark.index - 1]
        sep = (text[scalars[0].end_mark.index:scalars[1].start_mark.index]
               if len(scalars) > 1 else ", ")
        q = quote(scalars[0])
        new = self.lane.for_list(len(scalars))
        self.add("list", node, "[" + lead + sep.join(f"{q}{v}{q}" for v in new) + trail + "]", where)

    def expr(self, node: yaml.ScalarNode, where: str):
        start = node.start_mark.index
        span = self.s.text[start:node.end_mark.index]

        def repl(m: re.Match) -> str:
            count = len(re.findall(r'"3\.\d+"', m.group(0)))
            return "[" + ",".join(f'"{v}"' for v in self.lane.for_list(count)) + "]"

        new = JSON_LIST_RE.sub(repl, span)
        if LITERAL_RE.search(JSON_LIST_RE.sub("", span)):
            self.s.problems.append(f"{where}: version literal outside a JSON list in expression")
            return
        self.add("expr", node, new, where)

    # -- resolution ------------------------------------------------------------
    def value(self, node, where, *, step=None, job=None, matrix_keys=None):
        """Classify a python-version input value."""
        if node is None:
            return
        if isinstance(node, yaml.SequenceNode):
            self.flow_list(node, where)  # reusable-workflow input given a list
            return
        if not isinstance(node, yaml.ScalarNode):
            self.s.problems.append(f"{where}: unsupported python-version node")
            return
        raw = node.value.strip()
        if VERSION_RE.match(raw):
            return self.pin(node, where)
        ref = REF_RE.match(raw)
        if ref:
            ctx, name = ref.groups()
            if ctx == "matrix":
                if matrix_keys is not None:
                    matrix_keys.add(name)
                return
            target = None
            if ctx == "env":
                for scope in (step, job, self.root):
                    target = mget(mget(scope, "env"), name)
                    if target is not None:
                        break
            else:  # inputs
                on = mget(self.root, "on")
                for trigger in ("workflow_call", "workflow_dispatch"):
                    target = mget(mget(mget(mget(on, trigger), "inputs"), name), "default")
                    if target is not None:
                        break
                if target is None:
                    target = mget(mget(mget(self.root, "inputs"), name), "default")
            if isinstance(target, yaml.ScalarNode) and VERSION_RE.match(target.value.strip()):
                return self.pin(target, f"{where} -> {ctx}.{name}")
            elif target is not None and LITERAL_RE.search(getattr(target, "value", "") or ""):
                self.s.problems.append(f"{where}: {ctx}.{name} has an unrecognised version value")
            return
        if JSON_LIST_RE.search(raw):
            self.expr(node, where)
            return
        if LITERAL_RE.search(raw):
            self.s.problems.append(f"{where}: unrecognised version expression {raw!r}")

    def steps(self, steps_node, where, job=None, matrix_keys=None) -> list[str]:
        pinned = []
        for idx, step in enumerate(items(steps_node)):
            uses = mget(step, "uses")
            if isinstance(uses, yaml.ScalarNode) and uses.value.startswith("actions/setup-python@"):
                old = self.value(mget(mget(step, "with"), "python-version"),
                                 f"{where}.steps[{idx}]", step=step, job=job, matrix_keys=matrix_keys)
                if old:
                    pinned.append(old)
                    self.relabel(mget(step, "name"), old, self.lane.pin, f"{where}.steps[{idx}].name")
        return pinned

    def matrix(self, job, keys, where) -> dict[str, dict[str, str]]:
        """Rewrite python matrix values; return old->new role maps per matrix key."""
        maps: dict[str, dict[str, str]] = {}
        matrix = mget(mget(job, "strategy"), "matrix")
        if matrix is None or not keys or isinstance(matrix, yaml.ScalarNode):
            return maps  # expression matrices carry no literals; conditions() flags any that leak
        for key in sorted(keys):
            node = mget(matrix, key)
            entries = []  # (section, item, value node)
            for section in ("include", "exclude"):
                for item in items(mget(matrix, section)):
                    val = mget(item, key)
                    if isinstance(val, yaml.ScalarNode) and VERSION_RE.match(val.value.strip()):
                        entries.append((section, item, val))
                    elif val is not None:
                        self.s.problems.append(f"{where}.matrix.{section}.{key}: non-literal value")
            if node is not None and entries:
                self.s.problems.append(f"{where}.matrix.{key}: list plus include/exclude; migrate by hand")
                continue
            if isinstance(node, yaml.SequenceNode):
                self.flow_list(node, f"{where}.matrix.{key}")
                old = [n.value.strip() for n in node.value if isinstance(n, yaml.ScalarNode)]
                if old:
                    maps[key] = self.lane.role_map(old)
            elif isinstance(node, yaml.ScalarNode):
                self.value(node, f"{where}.matrix.{key}")
            if entries:
                try:
                    mapping = self.lane.for_roles([v.value.strip() for _, _, v in entries])
                except SyncError as exc:
                    self.s.problems.append(f"{where}.matrix.{key}: {exc}")
                    continue
                maps[key] = mapping
                seen: dict[str, set] = {"include": set(), "exclude": set()}
                for section, item, val in entries:
                    signature = tuple(sorted(
                        (k.value, mapping[v.value.strip()] if v is val else getattr(v, "value", repr(v)))
                        for k, v in item.value))
                    if signature in seen[section]:
                        self.drop_item(item, f"{where}.matrix.{section}")
                        continue
                    seen[section].add(signature)
                    q = quote(val)
                    self.add("roles", val, f"{q}{mapping[val.value.strip()]}{q}", f"{where}.matrix.{key}")
        return maps

    def drop_item(self, item, where):
        """Delete a whole include/exclude entry (its `- ...` line(s)) that became a duplicate."""
        text = self.s.text
        start = text.rfind("\n", 0, item.start_mark.index) + 1
        # Flow entries end at '}'; a block mapping's end_mark can sit on the next
        # entry's line, so for block style use the last value's end instead.
        anchor = item.end_mark.index if item.flow_style else item.value[-1][1].end_mark.index
        end = text.find("\n", anchor)
        end = len(text) if end < 0 else end + 1
        if not text[start:item.start_mark.index].strip().startswith("-"):
            self.s.problems.append(f"{where}: cannot locate entry to drop; migrate by hand")
            return
        self.add_span("drop", start, end, "", where)

    def run(self):
        try:
            self.root = yaml.compose(self.s.text, Loader=yaml.SafeLoader)
        except yaml.YAMLError as exc:
            self.s.problems.append(f"YAML parse error: {exc}")
            return
        if self.root is None:
            return
        runs = mget(self.root, "runs")
        if runs is not None:  # composite action
            self.steps(mget(runs, "steps"), "runs")
            return
        jobs = mget(self.root, "jobs")
        if not isinstance(jobs, yaml.MappingNode):
            return
        header = self.s.text[:jobs.start_mark.index]
        on = mget(self.root, "on")
        if on is not None:  # trigger path filters say nothing about what a job installs
            header = header.replace(self.s.text[on.start_mark.index:on.end_mark.index], "")
        for key_node, job in jobs.value:
            where = f"jobs.{key_node.value}"
            # Caps apply per job: workflow header (on/env) plus this job's own text.
            job_text = self.s.text[key_node.start_mark.index:job.end_mark.index]
            self.lane = self.policy.lane(self.s.rel, header + job_text, job=key_node.value)
            keys: set[str] = set()
            pinned = self.steps(mget(job, "steps"), where, job=job, matrix_keys=keys)
            with_ = mget(job, "with")  # reusable workflow call
            if isinstance(mget(job, "uses"), yaml.ScalarNode) and isinstance(with_, yaml.MappingNode):
                for k, v in with_.value:
                    if "python" in k.value.lower():
                        old = self.value(v, f"{where}.with.{k.value}", job=job, matrix_keys=keys)
                        if old:
                            pinned.append(old)
            maps = self.matrix(job, keys, where)
            self.conditions(mget(job, "if"), maps, f"{where}.if")
            for idx, step in enumerate(items(mget(job, "steps"))):
                self.conditions(mget(step, "if"), maps, f"{where}.steps[{idx}].if")
            if len(set(pinned)) == 1 and not keys:
                self.relabel(mget(job, "name"), pinned[0], self.lane.pin, f"{where}.name")


def workflow_files(root: Path) -> list[Path]:
    found: set[Path] = set()
    for pattern in WORKFLOW_GLOBS:
        found.update(root.glob(pattern))
    return sorted(found)


def scan_all(root: Path, policy: Policy) -> list[FileScan]:
    scans = []
    for path in workflow_files(root):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        scan = FileScan(rel, text, policy.lane(rel, text))
        Scanner(scan, policy).run()
        scans.append(scan)
    return scans


# --------------------------------------------------------------------------- derived files


def derived_updates(root: Path, policy: Policy) -> list[tuple[Path, str, str, list[str]]]:
    """Return (path, old_text, new_text, problems) for each derived file."""
    out = []
    for spec in policy.derived:
        path = root / spec["path"]
        version = policy.role_value(spec["value"])
        rendered = version.replace(".", "") if spec.get("format") == "nodot" else version
        if not path.exists():
            if spec.get("create"):
                out.append((path, "", f"{rendered}\n", []))
            else:
                out.append((path, "", "", [f"{spec['path']}: missing"]))
            continue
        old = path.read_text(encoding="utf-8")
        pattern = re.compile(spec["pattern"], re.M)
        if not pattern.search(old):
            out.append((path, old, old, [f"{spec['path']}: pattern {spec['pattern']!r} not found"]))
            continue
        new = pattern.sub(lambda m: m.group(0)[:m.start(1) - m.start(0)] + rendered
                          + m.group(0)[m.end(1) - m.start(0):], old)
        out.append((path, old, new, []))
    return out


# --------------------------------------------------------------------------- commands


def cmd_report(root: Path, policy: Policy) -> int:
    scans = scan_all(root, policy)
    total = 0
    for scan in scans:
        if not scan.sites and not scan.problems:
            continue
        cap = f"  [cap: {scan.lane.cap}]" if scan.lane.cap else ""
        print(f"{scan.rel}{cap}")
        for site in sorted(scan.sites, key=lambda s: s.start):
            mark = "" if site.old == site.new else "  -> " + site.new.replace("\n", " ")
            print(f"  L{site.line:<4} {site.kind:<5} {site.old.strip()[:70]}{mark}")
            total += 1
        for problem in scan.problems:
            print(f"  !! {problem}")
    print(f"\n{total} version sites in {sum(1 for s in scans if s.sites)} files")
    return 0


def stray_literals(scan: FileScan, policy: Policy) -> list[str]:
    """Version literals that bypass the SSOT: hard-coded python-version values in
    scripts/JSON, and end-of-life versions anywhere outside comments."""
    spans = [(s.start, s.end) for s in scan.sites]
    found = []

    def covered(pos):
        return any(a <= pos < b for a, b in spans)

    def comment(pos):
        line_start = scan.text.rfind("\n", 0, pos) + 1
        return scan.text[line_start:pos].lstrip().startswith("#")

    for m in STRAY_RE.finditer(scan.text):
        if not covered(m.start(1)) and not comment(m.start(1)):
            line = scan.text.count("\n", 0, m.start(1)) + 1
            found.append(f"L{line}: hard-coded python-version {m.group(1)} outside a managed site "
                         f"(read {LANES_VIEW_PATH.as_posix()} instead)")
    if scan.rel not in policy.canary and scan.rel not in policy.held:
        for m in LITERAL_RE.finditer(scan.text):
            if m.group(0) in policy.end_of_life and not covered(m.start()) and not comment(m.start()):
                line_start = scan.text.rfind("\n", 0, m.start()) + 1
                line_end = scan.text.find("\n", m.end())
                if re.search(r"py", scan.text[line_start:line_end if line_end >= 0 else None], re.I):
                    line = scan.text.count("\n", 0, m.start()) + 1
                    found.append(f"L{line}: end-of-life Python {m.group(0)} referenced")
    return found


def lane_declarations(scan: FileScan) -> list[str]:
    """Files that read the lanes view must declare the lane the SSOT assigns them."""
    path_filter = re.compile(r"^\s*-\s*['\"]?" + re.escape(LANES_VIEW_PATH.as_posix()) + r"['\"]?\s*$")
    if not any(LANES_VIEW_PATH.as_posix() in line and not path_filter.match(line)
               for line in scan.text.splitlines()):
        return []  # absent, or only named in an `on.*.paths` trigger filter
    declared = set(LANE_DECL_RE.findall(scan.text))
    if declared != {scan.lane.name}:
        return [f"reads {LANES_VIEW_PATH.as_posix()} so must declare PYTHON_LANE: {scan.lane.name} "
                f"(found {sorted(declared) or 'none'})"]
    return []


def problems_and_drift(root: Path, policy: Policy):
    scans = scan_all(root, policy)
    for scan in scans:
        scan.problems += stray_literals(scan, policy) + lane_declarations(scan)
    problems = [f"{s.rel}: {p}" for s in scans for p in s.problems]
    drift = [s for s in scans if s.synced_text() != s.text and s.rel not in policy.held]
    for rel in policy.held:
        if not (root / rel).exists():
            problems.append(f"{rel}: held in SSOT but missing")
    for name, spec in policy.caps.items():
        for entry in spec.get("exempt_jobs", []):
            rel, _, job = entry.rpartition(":")
            path = root / rel
            jobs = {}
            if path.exists():
                loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                jobs = loaded.get("jobs") or {}
            if job not in jobs:
                problems.append(f"cap {name}: exempt job {entry} does not exist")
    derived = derived_updates(root, policy)
    view_path = root / LANES_VIEW_PATH
    view_old = view_path.read_text(encoding="utf-8") if view_path.exists() else ""
    derived.append((view_path, view_old, policy.lanes_view(), []))
    problems += [p for *_, probs in derived for p in probs]
    derived_drift = [(p, o, n) for p, o, n, probs in derived if not probs and o != n]
    for rel in policy.canary:
        path = root / rel
        if not path.exists():
            problems.append(f"{rel}: canary workflow listed in SSOT but missing")
        elif "allow-prereleases: true" not in path.read_text(encoding="utf-8"):
            problems.append(f"{rel}: canary must set allow-prereleases: true")
    return scans, problems, drift, derived_drift


def cmd_check(root: Path, policy: Policy) -> int:
    scans, problems, drift, derived_drift = problems_and_drift(root, policy)
    for problem in problems:
        print(f"UNHANDLED {problem}")
    for scan in drift:
        for site in scan.sites:
            if site.old != site.new:
                print(f"DRIFT     {scan.rel}:{site.line} {site.old.strip()[:60]} != {site.new.strip()[:60]}")
    for path, _, _ in derived_drift:
        print(f"DRIFT     {path.relative_to(root).as_posix()} (derived file)")
    for scan in scans:
        if scan.rel in policy.held and scan.synced_text() != scan.text:
            print(f"HELD      {scan.rel}: {policy.held[scan.rel]}")
    if problems or drift or derived_drift:
        print("\nFix: python tools/ci/python_versions.py sync  (authority: ssot/python_versions.yaml)")
        return 1
    print(f"OK: workflows and derived files match ssot/python_versions.yaml "
          f"(supported {policy.supported[0]}-{policy.supported[-1]}, default {policy.default})")
    return 0


def cmd_sync(root: Path, policy: Policy) -> int:
    scans, problems, drift, derived_drift = problems_and_drift(root, policy)
    if problems:
        for problem in problems:
            print(f"UNHANDLED {problem}")
        print("\nRefusing to sync while unhandled sites exist.")
        return 2
    for scan in drift:
        new = scan.synced_text()
        yaml.compose(new, Loader=yaml.SafeLoader)  # must still parse
        (root / scan.rel).write_text(new, encoding="utf-8")
    for path, _, new in derived_drift:
        path.write_text(new, encoding="utf-8")
    print(f"synced {len(drift)} workflow files, {len(derived_drift)} derived files")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("report", "check", "sync"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        policy = Policy.load(args.root)
    except (OSError, KeyError, SyncError, yaml.YAMLError) as exc:
        print(f"invalid {SSOT_PATH}: {exc}", file=sys.stderr)
        return 2
    return {"report": cmd_report, "check": cmd_check, "sync": cmd_sync}[args.command](args.root, policy)


if __name__ == "__main__":
    sys.exit(main())
