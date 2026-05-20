/**
 * GBOGEB/ABACUS Theme Switcher
 * Implements SEMANTIC_THEME.yaml resolution rules:
 *   - Auto-detect via prefers-color-scheme
 *   - Persist preference to localStorage
 *   - 200ms transition
 */
(function () {
  'use strict';

  const STORAGE_KEY = 'gbogeb-theme-preference';
  const TRANSITION_DURATION = 200;

  function getPreferred() {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) return stored;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(STORAGE_KEY, theme);
  }

  // Apply on load
  applyTheme(getPreferred());

  // Listen for system preference changes
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function (e) {
    if (!localStorage.getItem(STORAGE_KEY)) {
      applyTheme(e.matches ? 'dark' : 'light');
    }
  });

  // Expose toggle for UI
  window.gbogeb = window.gbogeb || {};
  window.gbogeb.toggleTheme = function () {
    var current = document.documentElement.getAttribute('data-theme');
    applyTheme(current === 'dark' ? 'light' : 'dark');
  };
})();
