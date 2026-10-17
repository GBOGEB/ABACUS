"""Produce a source-identity conservative coverage evolution report."""

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from obligation_lineage import compare, parse_artifact


def main():
    parser = argparse.ArgumentParser()
    for label in ("before", "after"):
        parser.add_argument("--" + label + "-json", type=pathlib.Path, required=True)
        parser.add_argument(
            "--" + label + "-manifest", type=pathlib.Path, required=True
        )
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()
    values = []
    for label in ("before", "after"):
        raw = getattr(args, label + "_json").read_bytes()
        manifest = json.loads(
            getattr(args, label + "_manifest").read_text(encoding="utf-8")
        )
        values.append(parse_artifact(raw, manifest))
    result = compare(*values)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "before_sha": result["before_sha"],
                "after_sha": result["after_sha"],
                "status": result["status"],
                "merge_admission": result["merge_admission"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
