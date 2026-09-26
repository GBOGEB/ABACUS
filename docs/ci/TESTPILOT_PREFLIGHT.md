# ABACUS TestPilot — pre-GitHub defect gate

TestPilot shifts deterministic defect discovery left of GitHub Actions. It does **not**
replace the authoritative CI suite and it never lowers the 70% DMAIC coverage gate.

## One-time setup

```powershell
python -m pip install -r requirements-dev.txt
pre-commit install
```

## Normal use

Fast local pilot:

```powershell
.\scripts\testpilot.ps1
```

Safe lint repair, then re-check:

```powershell
.\scripts\testpilot.ps1 -Fix
```

Full local regression check with the current recovery floor:

```powershell
.\scripts\testpilot.ps1 -Mode full
```

GitHub-parity coverage gate:

```powershell
.\scripts\testpilot.ps1 -Mode gate
```

The gate mode defaults to **70%**. Do not lower it to make a failing change green.

## What fast mode catches before push

- unresolved merge-conflict markers;
- Python syntax/compile errors in changed files;
- JSON/TOML/YAML parse errors;
- Ruff findings when Ruff is installed;
- pytest collection failures;
- the live DMAIC super-bridge smoke/E2E contract.

The receipt is written to `.testpilot/last_receipt.json`.

## Repair policy

`-Fix` is intentionally narrow. It permits only Ruff's deterministic safe fixes.
TestPilot does not rewrite assertions, alter expected values, suppress failing tests,
change coverage scope, or reduce thresholds.

## Coverage modes

- `fast`: no coverage gate; appropriate for pre-commit.
- `full`: full DMAIC suite with a default **25% regression floor** while #1391
  recovers coverage. This is a temporary anti-regression floor, not a quality target.
- `gate`: full DMAIC suite with the authoritative **70%** floor.

Once #1391 reaches staged milestones, the full-mode regression floor should ratchet
upward (40 -> 55 -> 70) and never move backward without an explicit governed decision.
