#!/usr/bin/env python3
"""Read-only tracked configuration and DAG syntax census.

YAML uses PyYAML BaseLoader composition: keys such as GitHub Actions 'on'
remain strings. Syntax, schema, executable behavior and style are separate.
Never silently rewrite YAML, TOML, JSON, INI, Mermaid or Graphviz files.
"""
from __future__ import annotations

import argparse
import ast
import configparser
import json
import subprocess
import tomllib
from collections import Counter
from pathlib import Path

import yaml

SCHEMA = "codepurple.abacus.config-surface-audit.v1"
EXTS = {".yaml": "yaml", ".yml": "yaml", ".json": "json",
        ".toml": "toml", ".ini": "ini", ".mmd": "mermaid",
        ".dot": "graphviz"}
LIMIT = 8_000_000


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + repr(key))
        result[key] = value
    return result


def check_yaml(raw: str, workflow: bool = False) -> list:
    documents = list(yaml.compose_all(raw, Loader=yaml.BaseLoader))
    if not documents:
        raise ValueError("empty YAML")
    if workflow and len(documents) != 1:
        raise ValueError("workflow must contain exactly one YAML document")
    seen_nodes = set()
    def walk(node):
        if id(node) in seen_nodes:
            return
        seen_nodes.add(id(node))
        if isinstance(node, yaml.MappingNode):
            keys = set()
            for key, val in node.value:
                if not isinstance(key, yaml.ScalarNode):
                    raise ValueError("complex mapping key")
                if key.value in keys:
                    raise ValueError("duplicate YAML key: " + repr(key.value))
                keys.add(key.value)
                walk(val)
        elif isinstance(node, yaml.SequenceNode):
            for val in node.value:
                walk(val)
    for doc in documents:
        walk(doc)
    concerns = []
    if workflow:
        data = yaml.load(raw, Loader=yaml.BaseLoader)
        if not isinstance(data, dict):
            raise ValueError("workflow must be a mapping")
        jobs = data.get("jobs", {})
        if not isinstance(jobs, dict):
            raise ValueError("workflow jobs must be mapping")
        links = {}
        for name, job in jobs.items():
            if not isinstance(job, dict):
                raise ValueError("workflow job must be mapping: " + name)
            dep = job.get("needs", [])
            if isinstance(dep, str):
                dep = [dep]
            if not isinstance(dep, list):
                raise ValueError("workflow needs must be sequence or string")
            if any(not isinstance(x, str) for x in dep):
                raise ValueError("workflow needs entry must be string")
            if any("${{" in x for x in dep):
                concerns.append("DYNAMIC_JOB_NEEDS_NOT_RESOLVED")
                links[name] = []
                continue
            if any(x not in jobs for x in dep):
                raise ValueError("unknown workflow job in needs: " + name)
            links[name] = dep
        visited, active = set(), set()
        def visit(name):
            if name in active:
                raise ValueError("cyclic workflow job needs")
            if name in visited:
                return
            active.add(name)
            for before in links[name]:
                visit(before)
            active.remove(name)
            visited.add(name)
        for name in links:
            visit(name)
    return sorted(set(concerns))


def check_text(path: str, text: str) -> tuple[str, list]:
    suffix = Path(path).suffix.lower()
    if path.endswith("__init__.py"):
        ast.parse(text, filename=path)
        return "PYTHON_INIT", []
    kind = EXTS.get(suffix)
    if kind == "yaml":
        concerns = check_yaml(text, path.startswith(".github/workflows/"))
        return "YAML", concerns
    if kind == "json":
        json.loads(
            text,
            object_pairs_hook=unique_pairs,
            parse_constant=lambda x: (_ for _ in ()).throw(
                ValueError("non-finite JSON literal: " + x)
            ),
        )
        return "JSON", []
    if kind == "toml":
        tomllib.loads(text)
        return "TOML", []
    if kind == "ini":
        configparser.ConfigParser(interpolation=None, strict=True).read_string(text)
        return "INI", []
    if kind == "mermaid":
        return "MERMAID", ["NO_BUILTIN_MERMAID_SEMANTIC_PARSER"]
    if kind == "graphviz":
        return "GRAPHVIZ", ["EXTERNAL_DOT_VALIDATOR_NOT_EXECUTED"]
    return "OTHER", []


def discover(root: Path) -> list[str]:
    p = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
    )
    return sorted(x.decode("utf-8") for x in p.stdout.split(bytes([0])) if x)


def audit(root: Path, paths: list[str], limit: int = LIMIT) -> dict:
    counts = Counter()
    findings = []
    seen = set()
    for name in paths:
        if name in seen:
            raise ValueError("duplicate source path in census")
        seen.add(name)
        if (not name or name.startswith("/") or "\\" in name or
                ".." in Path(name).parts):
            raise ValueError("unsafe source path")
        if not (name.endswith("__init__.py") or
                Path(name).suffix.lower() in EXTS):
            continue
        path = root / name
        try:
            if not path.is_file():
                raise ValueError("tracked file absent from checkout")
            if path.stat().st_size > limit:
                counts["UNKNOWN_OVERSIZE"] += 1
                findings.append({"path": name, "state": "UNKNOWN_OVERSIZE"})
                continue
            raw = path.read_text(encoding="utf-8")
            kind, concerns = check_text(name, raw)
            if concerns:
                counts["UNVERIFIED_SEMANTICS"] += 1
                findings.append({
                    "path": name, "state": "UNVERIFIED_SEMANTICS",
                    "kind": kind, "reasons": concerns,
                })
            else:
                counts["SYNTAX_PASS"] += 1
        except (OSError, UnicodeError, ValueError, yaml.YAMLError,
                json.JSONDecodeError, SyntaxError,
                configparser.Error, tomllib.TOMLDecodeError) as exc:
            counts["SYNTAX_RED"] += 1
            findings.append({
                "path": name, "state": "SYNTAX_RED",
                "error": str(exc)[:240],
            })
    return {
        "schema": SCHEMA,
        "source": "GIT_LS_FILES_TRACKED_ONLY",
        "counts": dict(sorted(counts.items())),
        "selected_files": sum(counts.values()),
        "findings": findings,
        "untracked_or_ignored_files": None,
        "style_validation": "NOT_PERFORMED_SEPARATE_YAMLLINT_FORMATTER",
        "github_actionlint": "NOT_PERFORMED",
        "mermaid_graphviz_semantics": "NOT_PERFORMED",
        "runtime_integration_verified": False,
        "source_mutation": False,
        "merge_admission": "HOLD",
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--strict", action="store_true")
    a = p.parse_args(argv)
    result = audit(a.root, discover(a.root))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 1 if a.strict and result["counts"].get("SYNTAX_RED", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
