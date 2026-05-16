# Topic-Specific Repository Assessment

> **Generated:** 2026-05-16 22:34

## Current State: Mono-Repo

ABACUS is currently a mono-repo containing all versions, tools, and documentation.

## Self-Contained Modules Identified

| Module | Directory | Coupling | Cohesion | Standalone? |
|--------|-----------|----------|----------|-------------|
| Cryo Dashboard | `cryo_dashboard_v0_3_0/` | Low | High | ✅ Could be separate |
| RTM Integration | `rtm_integration/` | Medium | High | ✅ Could be separate |
| DMAIC V3 Engine | `DMAIC_V3/` | High | High | ⚠️ Core system |
| Local MCP | `local_mcp/` | Medium | Medium | ✅ Could be separate |
| Staging Bridge | `staging/` | High | Medium | ❌ Integration component |
| DMAIC Sprint | `dmaic-sprint-system/` | Low | High | ✅ Could be separate |
| Scripts | `scripts/` | Medium | Low | ❌ Utility collection |

## Recommendations

### Keep as Mono-Repo (Recommended for Now)
**Pros:**
- Single source of truth for all versions
- Cross-component integration is straightforward
- DOW governance applies uniformly
- Version lineage is clear in single git history
- Simpler CI/CD (one pipeline)

**Cons:**
- Large repository (~50MB+)
- Mixed concerns (cryo-specific + generic tools)
- Complex for new contributors
- Many workflows (32+)

### Potential Splits (Future Consideration)

1. **`cryo-dashboard`** — Standalone visualization repo with GitHub Pages
   - Low coupling, high cohesion, self-contained HTML/JS
   - Could have its own GitHub Pages deployment
   
2. **`abacus-rtm`** — RTM integration tools
   - QPLANT-specific requirements tracking
   - Excel + Python, could serve other projects
   
3. **`abacus-dmaic-engine`** — Core DMAIC V3 engine
   - Only if engine stabilizes and API freezes
   - Currently too coupled to split safely

### Decision Criteria
Split only when:
1. Module has stable API boundaries
2. Independent release cycle needed
3. Different team ownership
4. GitHub Pages needed for specific tool
5. Security/access isolation required

## Conclusion
**Stay mono-repo for now.** The system is still maturing and splitting prematurely 
would add coordination overhead without clear benefit. Revisit after P0 issues are resolved.
