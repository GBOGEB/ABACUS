/**
 * GBOGEB/ABACUS — Hub Landing Page Interactive Logic
 *
 * Loads knowledge_topology.json and renders node cards dynamically.
 * Provides category filtering, search, and smooth scroll navigation.
 */

(function () {
  'use strict';

  // ── Topology Data (embedded fallback; also loaded from JSON) ──────
  let topologyData = null;

  /**
   * Fetch topology JSON — tries relative path first, falls back to embedded.
   */
  async function loadTopology() {
    try {
      const resp = await fetch('../config/knowledge_topology.json');
      if (resp.ok) {
        topologyData = await resp.json();
        return;
      }
    } catch (_) { /* fall through */ }

    // Fallback: try alternate path (GitHub Pages flat structure)
    try {
      const resp2 = await fetch('./config/knowledge_topology.json');
      if (resp2.ok) {
        topologyData = await resp2.json();
        return;
      }
    } catch (_) { /* fall through */ }

    console.warn('[Hub] Could not load knowledge_topology.json — using embedded data.');
    topologyData = getEmbeddedTopology();
  }

  /**
   * Embedded topology fallback for file:// protocol or offline use.
   */
  function getEmbeddedTopology() {
    return {
      nodes: [
        {id:"GBA-GOV-001",repo:"GBA",label:"Render Rules Engine",category:"governance",path:"engines/RENDER_RULES.md",description:"Master specification for all rendering governance rules.",outputs:[],cross_repo_deps:[]},
        {id:"GBA-GOV-002",repo:"GBA",label:"Render Linter",category:"governance",path:"engines/RENDER_LINTER.py",description:"Python linter enforcing RENDER_RULES against Markdown/HTML content.",outputs:[],cross_repo_deps:[]},
        {id:"GBA-GOV-003",repo:"GBA",label:"WCAG Contrast Checker",category:"governance",path:"engines/WCAG_CONTRAST_CHECKER.py",description:"Validates WCAG AA contrast ratios across all theme color pairs.",outputs:[],cross_repo_deps:["GBC-THEME-001"]},
        {id:"GBA-GOV-004",repo:"GBA",label:"Slide ID Enforcer",category:"governance",path:"engines/SLIDE_ID_ENFORCER.py",description:"Validates slide ID format, uniqueness, and immutability.",outputs:[],cross_repo_deps:[]},
        {id:"GBA-GOV-005",repo:"GBA",label:"Semantic Theme",category:"theme",path:"engines/SEMANTIC_THEME.yaml",description:"CSS custom property token definitions for light/dark themes.",outputs:[],cross_repo_deps:["GBC-THEME-001"]},
        {id:"GBA-GOV-006",repo:"GBA",label:"Layout Contracts",category:"governance",path:"engines/LAYOUT_CONTRACTS.yaml",description:"Deterministic spacing, typography scale, and layout rules.",outputs:[],cross_repo_deps:["GBC-LAYOUT-001"]},
        {id:"GBA-GOV-007",repo:"GBA",label:"Lineage Schema",category:"lineage",path:"engines/LINEAGE_SCHEMA.yaml",description:"JSON Schema for lineage_manifest.json — asset tracking structure.",outputs:[],cross_repo_deps:[]},
        {id:"GBA-LIN-001",repo:"GBA",label:"Verification Hook",category:"lineage",path:"engines/verification_hook.py",description:"Binary asset processor — SHA256 hashing, .mock sidecar creation, manifest management.",outputs:[],cross_repo_deps:["GBC-ASSET-001"]},
        {id:"GBA-LIN-002",repo:"GBA",label:"Lineage Manifest",category:"lineage",path:"_data/lineage_manifest.json",description:"Central registry of all processed binary assets with SHA256 hashes.",outputs:[],cross_repo_deps:[]},
        {id:"GBA-CI-001",repo:"GBA",label:"Governance Validation Pipeline",category:"ci_cd",path:".github/workflows/governance-validation.yml",description:"CI/CD: lint, contrast, slide-ids, tests — runs on PR and push.",outputs:[],cross_repo_deps:[]},
        {id:"GBA-CI-002",repo:"GBA",label:"Asset Verification Pipeline",category:"ci_cd",path:".github/workflows/asset-verification.yml",description:"CI/CD for Input_Master/ binary asset verification.",outputs:[],cross_repo_deps:[]},
        {id:"GBA-CI-003",repo:"GBA",label:"Archive & Deploy Pipeline",category:"ci_cd",path:".github/workflows/archive-deploy.yml",description:"Generates workspace_bundle.tar.gz and deploys to GitHub Pages.",outputs:[],cross_repo_deps:[]},
        {id:"GBA-WEB-001",repo:"GBA",label:"Hub Landing Page",category:"web",path:"web/index.html",description:"Central navigation hub with download banner and topology cards.",outputs:[],cross_repo_deps:[]},
        {id:"GBA-EX-001",repo:"GBA",label:"Multi-View Engineering Tool",category:"example",path:"examples/multi_view_workspace/",description:"SPA demonstrating split-pane YAML→render pipeline with HMI, Marp, and report views.",outputs:[],cross_repo_deps:[]},
        {id:"GBA-CFG-001",repo:"GBA",label:"Governance Tuning",category:"config",path:"config/governance_tuning.yaml",description:"Central configuration for governance strictness and linter rules.",outputs:[],cross_repo_deps:[]},
        {id:"GBA-CFG-002",repo:"GBA",label:"Knowledge Topology",category:"config",path:"config/knowledge_topology.json",description:"Cross-repository node mapping and dependency graph.",outputs:[],cross_repo_deps:[]},
        {id:"GBA-CFG-003",repo:"GBA",label:"Stakeholder Registry",category:"config",path:"config/stakeholder_registry.yaml",description:"Communication routes mapping stakeholder groups to preferred formats.",outputs:[],cross_repo_deps:[]},
        {id:"GBC-THEME-001",repo:"GBC",label:"Design Tokens",category:"theme",path:"themes/tokens.yaml",description:"Canonical color palette, typography scale, and spacing tokens from CODEX.",outputs:[],cross_repo_deps:[]},
        {id:"GBC-LAYOUT-001",repo:"GBC",label:"Layout Blueprints",category:"layout",path:"layouts/",description:"Master layout specifications and grid definitions from CODEX.",outputs:[],cross_repo_deps:[]},
        {id:"GBC-ASSET-001",repo:"GBC",label:"Binary Master Assets",category:"asset",path:"exports/",description:"Source PPTX, PDF, and image files exported from CODEX.",outputs:[],cross_repo_deps:[]}
      ],
      edges: [],
      categories: {
        governance:{color:"#6d28d9",icon:"fa-shield-halved",label:"Governance Engine"},
        lineage:{color:"#0891b2",icon:"fa-link",label:"Knowledge Lineage"},
        theme:{color:"#d946ef",icon:"fa-palette",label:"Theme & Design"},
        ci_cd:{color:"#f59e0b",icon:"fa-gears",label:"CI/CD Pipeline"},
        web:{color:"#10b981",icon:"fa-globe",label:"Web Interface"},
        example:{color:"#3b82f6",icon:"fa-flask",label:"Example / Demo"},
        config:{color:"#64748b",icon:"fa-sliders",label:"Configuration"},
        layout:{color:"#ec4899",icon:"fa-table-columns",label:"Layout"},
        asset:{color:"#ef4444",icon:"fa-file-zipper",label:"Binary Asset"}
      }
    };
  }

  /**
   * Render node cards from topology data into #topologyGrid.
   */
  function renderTopologyCards() {
    const grid = document.getElementById('topologyGrid');
    if (!grid || !topologyData) return;

    const categories = topologyData.categories || {};
    const nodes = topologyData.nodes || [];

    // Only render GBA nodes (filter out GBC placeholder nodes)
    const gbaNodes = nodes.filter(n => n.repo === 'GBA');
    const gbcNodes = nodes.filter(n => n.repo === 'GBC');

    let html = '';

    // GBA nodes first
    gbaNodes.forEach(node => {
      const cat = categories[node.category] || {};
      const color = cat.color || '#60a5fa';
      const icon = cat.icon || 'fa-circle';
      const catLabel = cat.label || node.category;

      html += `
        <div class="node-card" style="--node-color: ${color}" data-category="${node.category}" data-repo="${node.repo}">
          <div class="card-header">
            <div class="card-icon"><i class="fas ${icon}"></i></div>
            <div>
              <div class="card-id">${node.id}</div>
              <div class="card-title">${node.label}</div>
            </div>
          </div>
          <div class="card-desc">${node.description}</div>
          <code class="card-path">${node.path}</code>
          <div class="card-tags">
            <span class="card-tag repo-gba">GBA</span>
            <span class="card-tag">${catLabel}</span>
            ${node.cross_repo_deps.length > 0 ? '<span class="card-tag repo-gbc">↔ GBC</span>' : ''}
          </div>
        </div>`;
    });

    // GBC nodes (dimmed, showing cross-repo relationship)
    gbcNodes.forEach(node => {
      const cat = categories[node.category] || {};
      const color = cat.color || '#a78bfa';
      const icon = cat.icon || 'fa-circle';
      const catLabel = cat.label || node.category;

      html += `
        <div class="node-card" style="--node-color: ${color}; opacity: 0.7;" data-category="${node.category}" data-repo="${node.repo}">
          <div class="card-header">
            <div class="card-icon"><i class="fas ${icon}"></i></div>
            <div>
              <div class="card-id">${node.id}</div>
              <div class="card-title">${node.label}</div>
            </div>
          </div>
          <div class="card-desc">${node.description}</div>
          <code class="card-path">${node.path}</code>
          <div class="card-tags">
            <span class="card-tag repo-gbc">GBC (CODEX)</span>
            <span class="card-tag">${catLabel}</span>
          </div>
        </div>`;
    });

    grid.innerHTML = html;
  }

  /**
   * Category filter buttons — show/hide node cards.
   */
  function setupFilters() {
    const filterBtns = document.querySelectorAll('[data-filter]');
    filterBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const filter = btn.dataset.filter;

        // Toggle active state
        filterBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        // Filter cards
        const cards = document.querySelectorAll('.node-card');
        cards.forEach(card => {
          if (filter === 'all') {
            card.style.display = '';
          } else if (filter === 'gba') {
            card.style.display = card.dataset.repo === 'GBA' ? '' : 'none';
          } else if (filter === 'gbc') {
            card.style.display = card.dataset.repo === 'GBC' ? '' : 'none';
          } else {
            card.style.display = card.dataset.category === filter ? '' : 'none';
          }
        });
      });
    });
  }

  /**
   * Smooth scroll for anchor links.
   */
  function setupSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', e => {
        e.preventDefault();
        const target = document.querySelector(anchor.getAttribute('href'));
        if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    });
  }

  /**
   * Update stats counters from topology data.
   */
  function updateStats() {
    if (!topologyData) return;
    const nodes = topologyData.nodes || [];
    const el = document.getElementById('statsInfo');
    if (!el) return;

    const gbaCount = nodes.filter(n => n.repo === 'GBA').length;
    const gbcCount = nodes.filter(n => n.repo === 'GBC').length;
    const edgeCount = (topologyData.edges || []).length;
    const crossRepo = (topologyData.edges || []).filter(e => e.type === 'cross_repo').length;

    el.textContent = `${gbaCount} GBA nodes · ${gbcCount} GBC nodes · ${edgeCount} edges (${crossRepo} cross-repo)`;
  }

  // ── Initialize ────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', async () => {
    await loadTopology();
    renderTopologyCards();
    setupFilters();
    setupSmoothScroll();
    updateStats();
  });
})();
