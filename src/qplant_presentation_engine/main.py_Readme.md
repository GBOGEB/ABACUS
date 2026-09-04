# src/qplant_presentation_engine/main.py — Presentation Engine smoke entry

## Purpose
One-shot CLI entry point (`python -m qplant_presentation_engine`) that runs
a "W001.1" runtime smoke test and prints a pass/fail report. No server, no
long-running process, no CLI arguments.

## Flow (ASCII)

    python -m qplant_presentation_engine
        │
        ▼
    __main__.py: from .main import main; SystemExit(main())
        │
        ▼
    main.py: main()
        │
        ▼
    runtime.py: run_runtime()
        ├─► metrics.load_metrics()
        ├─► truth_matrix.TRUTH_RULES  (checked non-empty)
        └─► validate.py: validate_runtime()
                ├─► import_module(package)               → package_import
                ├─► import_module(package + ".runtime")  → runtime_entry
                ├─► metrics.load_metrics()                → metrics_availability
                ├─► truth_matrix.TRUTH_RULES               → truth_matrix_availability
                └─► schema_validation.validate_canonical_schema() → schema_consistency
        │
        ▼
    print each report line; return exit_code (0/1)

## Dependencies (local)
- qplant_presentation_engine.runtime (run_runtime)
- qplant_presentation_engine.metrics (load_metrics)
- qplant_presentation_engine.truth_matrix (TRUTH_RULES)
- qplant_presentation_engine.validate (validate_runtime)
- qplant_presentation_engine.schema_validation (validate_canonical_schema, dynamically imported inside validate.py)

## Known failure modes (found in code, not hypothetical)
- `runtime._resolve_entrypoint_module()` does a filesystem probe
  (`parents[2] / "qplant_presentation_engine" / "__main__.py"`) to
  disambiguate between two possible package locations on disk (there is a
  top-level `qplant_presentation_engine/` directory *and*
  `src/qplant_presentation_engine/`) — this is a code smell indicating an
  unresolved duplicate-package situation in the repo, not a normal runtime
  concern. Not fixed here; needs a decision on which location is canonical.
- No CLI argument handling at all — `main()` takes no parameters, so this
  entry point cannot be pointed at a different config/target without
  editing source.

## Change log
- 2026-09-04: `validate.py` now logs the underlying exception
  (`logger.warning(..., exc_info=True)`) at each of its five check points
  before recording `False`. Previously every failure was swallowed into a
  bare boolean with no trace of cause — a FAIL in the printed report gave
  no way to tell "module missing" from "logic bug" from anything else
  without manually stripping the try/except and re-running.
