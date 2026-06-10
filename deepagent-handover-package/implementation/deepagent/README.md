# DeepAgent Apps Framework v2.0 — TypeScript Implementation

Production-ready TypeScript library providing DMAIC process management, KPI tracking, automation workflows, and recursive handover structures.

## Requirements

- **Node.js** >= 18.0.0
- **npm** (bundled with Node.js)

## Installation

```bash
cd deepagent-handover-package/implementation/deepagent/
npm install
```

## Build

Compile the TypeScript sources to JavaScript (emitted to `dist/`):

```bash
npm run build
```

This produces, in `dist/`:
- `*.js` — compiled CommonJS modules
- `*.d.ts` — TypeScript type declarations
- `*.js.map` / `*.d.ts.map` — source maps

### Available Scripts

| Script | Description |
|--------|-------------|
| `npm run build` | Compile TypeScript → `dist/` (JS + declarations + source maps) |
| `npm run build:watch` | Compile in watch mode (rebuild on file change) |
| `npm run typecheck` | Type-check only, no output emitted (`--noEmit`) |
| `npm run clean` | Remove the `dist/` output directory |
| `npm run rebuild` | `clean` + `build` |
| `npm test` | Placeholder — a real test suite is planned for v2.1 (see [ROADMAP.md](../../ROADMAP.md)) |

## Usage

After building, consume the compiled library:

```js
const { framework, createProject, dmaicManager, kpiManager } = require('./dist/index.js');

console.log(framework.getVersion());        // "2.0.0"
console.log(framework.getCapabilities());   // list of framework capabilities
```

Or, when developing in TypeScript, import directly from source:

```ts
import { framework, createProject } from './index';
```

## Module Overview

| File | Responsibility |
|------|----------------|
| `index.ts` | Main export barrel + `DeepAgentFramework` singleton |
| `framework.ts` | Core domain interfaces (project, KPI, automation, handover) |
| `automation.ts` | `AutomationEngine` — workflow registration & execution |
| `kpi.ts` | `KPIManager` — KPI registration, collection, reporting |
| `dmaic.ts` | `DMAICProcessManager` — Define→Measure→Analyze→Improve→Control |
| `handover.ts` | `HandoverManager` — recursive handover structure & validation |

## Notes

- `dist/` and `node_modules/` are git-ignored; build artifacts are generated locally and are not committed.
- The build is verified to compile cleanly (`tsc` exit 0) under TypeScript 5.9.x with `strict` mode enabled.
