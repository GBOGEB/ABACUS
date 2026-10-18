# CODE PURPLE W45 — Local Operator Workbench

The existing SUT Control Tower remains the read-only entry point. The
`/operator` page adds a bounded **local operator workstation**, not an agent
administrator, remote execution proxy, or GitHub merge authority.

## Start

From a trusted, checked-out ABACUS repository on your computer:

```bash
mkdir -p operator-inbox operator-receipts
python tools/everred_v3/sut_gui/server.py \
  --sut-root tools/everred_v3 \
  --abacus-root . \
  --operator-inbox ./operator-inbox \
  --operator-receipts ./operator-receipts \
  --enable-operator
```

Open `http://127.0.0.1:8765/operator`. Copy the per-process token displayed
in the Python terminal into the operator page. No token goes to GitHub.
The normal Control Tower remains at `http://127.0.0.1:8765/`.

On Windows PowerShell the existing launcher also accepts:

```powershell
.\tools\everred_v3\sut_gui\start-windows.ps1 `
  -SutRoot ".\tools\everred_v3" `
  -AbacusRoot "." `
  -InboxDir ".\operator-inbox" `
  -ReceiptDir ".\operator-receipts" `
  -EnableOperator
```

By default neither the original SUT testflight nor operator execution is
enabled. The operator console can display the task catalog without permission
to execute.

## Pipeline menu and decision boundaries

| Profile | Input | Behavior |
| --- | --- | --- |
| `python-tests` | None | Focused Mission Control Lite unit tests |
| `pipeline-3p` | None | One bounded 3P run in a fresh checkout |
| `binary-bridge` | One named inbox file | Derived QPS semantic package |
| `debug-compile` | None | Python compile and syntax preflight |
| `runner-tests` | None | Runner-wait source contracts |
| `task-census` | None | Local task/receipt census in temporary DB |
| `mcp-readiness` | None | BLOCKED: no authenticated MCP adapter |

The workbench accepts **only** the listed static commands; no web form accepts
a free-form shell command, arbitrary Python module, script path, environment
variable or remote MCP endpoint. For the binary bridge, valid inputs are
PDF, DOCX, XLSX, PPTX and HTML. Put originals in the inbox yourself.
The server validates name, extension, size, magic and SHA-256.

Use **Plan** to read the immutable checkout SHA, input hash and fixed argv.
Approve it explicitly with the local token and checkbox before Execute.
An input modified after Plan, an unrecognized profile, a stale commit, bad
token, changed file, unauthorized Host/Origin or invalid schedule is denied.

The clone is fresh and detached at the approved source SHA. The source tree
and binary originals are **not deleted or rewritten**. Generated outputs are
copied into `operator-receipts/<run_id>/artifacts/`, with an append-only
`receipt.json` recording derived file hashes, exact source commit, status,
commands, bounded stdout/stderr and local decision. Downloads recompute the
file digest before serving bytes and require the local execution token.

The I/O contract explicitly retains `KEEP_AWAIT_USER_APPROVAL` for original
disposition. There is **no delete or merge-versions endpoint**.

## Schedule and task state

Delay is 0–3600 seconds, one scheduled/active task at a time.
`SCHEDULED → RUNNING → PASS_LOCAL_ONLY | RED | TIMEOUT | ERROR`, or
`SCHEDULED → CANCELLED` before start. A changed checkout before dispatch
becomes `STALE_SOURCE`; a concurrently occupied executor becomes
`CAPACITY_HOLD`. A delayed task is *process-local and not durable*: if the
local server stops, the task will not automatically resume. The user must
reapprove it after restart. Do not claim Temporal, distributed dispatch or
persisted scheduler state from this limited local controller.

The clone and source review reduce accidental file damage, **but Python
code still executes with the user's OS permissions**. This is not a
container/microVM sandbox. Do not run untrusted branches or inputs expecting
malware isolation. Remote MCP and cross-repository operations require an
independently authenticated external authorizer, deny receipts, and controls
documented under Mission Control Lite security work packages.

## Native qualification

The existing `CODE PURPLE SUT GUI Contract` workflow exercises
`tools/everred_v3/sut_gui/tests/test_*.py` across Python 3.10/3.12.
This includes local Git-clone tests, authorization denials, stale input/SHA,
binary preservation, receipt checks and localhost HTTP negative controls.

Engineering acceptance requires terminal native job/attempt IDs, measured
branch and statement coverage, SUT GUI visual QA, security/A10 and
policy/inventory outputs, then eligible independent code review.

Local `PASS_LOCAL_ONLY` is never `MERGE_ADMISSION=PASS`, a root closed,
authenticated Crew/REX launch, an approved exception or security waiver.

## Existing owner work to reconcile

- [MCL #1978](https://github.com/GBOGEB/ABACUS/issues/1978):
  operator isolation, typed authorization, durable scheduler and GUI
- [Admission #1860](https://github.com/GBOGEB/ABACUS/issues/1860):
  mandatory checks, independent reviewer and blocked RED canary
- [BD/LDAB #1929](https://github.com/GBOGEB/ABACUS/issues/1929):
  joined root evidence and exact-SHA attribution
- [MIP #1991](https://github.com/GBOGEB/ABACUS/issues/1991):
  scope-matched branch and statement coverage
- [CODEX #989](https://github.com/GBOGEB/CODEX/issues/989):
  authenticated federation/consumer telemetry

Do not close or mark the above as verified from a successful local GUI run.
