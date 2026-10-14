# CODE PURPLE — Live HTML + local SUT controller

Standalone HTML can refresh GitHub's public read-only state directly. It is **not** continuously live when saved as `file:///.../index.html`; GitHub API calls require network access, and failures are UNKNOWN. Local pipeline execution requires `server.py`.

1. Clone or use a trusted local checkout of `GBOGEB/ABACUS` with `tools/everred_v3` present. Never run unknown pull-request code merely because a dashboard shows it.
2. Place the HTML/server files in `tools/everred_v3/sut_gui/`, or launch from any folder with an explicit `--sut-root`.
3. Run `python server.py --sut-root C:\path\to\ABACUS\tools\everred_v3 --enable-execution` on your PC.
4. Open `http://127.0.0.1:8765/`. Enter the one-time execution token printed in your own terminal, choose an allowlisted test profile and click Execute.
5. The local runner copies source/test/data into a temporary directory and never pushes, merges or dispatches GitHub workflows. It executes trusted checkout code with your current user permissions: **not a security sandbox**.

The server binds only to `127.0.0.1` and rejects cross-origin POSTs. Do not expose it through public port forwarding or proxy it beyond localhost. A `GITHUB_TOKEN` environment variable, if provided, is only used by the server for read-only GitHub API requests; it is never returned to the GUI. Without a token, the server uses public API GET requests.

Profiles: model-preflight, unit-tests, ledger-verify, pipeline-testflight. One run at a time; each step has a 180-second bound. No caller-supplied command or path is executable. Local tests do not grant release or merge approval.

Acceptance: `python -m unittest discover -s tests -q` within the GUI package for harness tests; `python server.py --sut-root ... --enable-execution`; check the browser in desktop, laptop and mobile viewports. Compare generated HTML source SHA and testflight receipts against the actual GitHub PR head.