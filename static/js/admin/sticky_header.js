/*
 * Keeps CSS variables in sync with the sticky admin header and breadcrumbs:
 *   --admin-header-h  height of #header (breadcrumbs stick right below it)
 *   --admin-sticky-h  header + breadcrumbs (sidebar, outline panel and anchor
 *                     jumps start below this)
 *   --admin-crumbs-h  breadcrumbs only (phones pin just the breadcrumbs)
 * The header wraps on narrow windows, so heights are observed, not hard-coded.
 */
(function () {
  'use strict';

  function measure() {
    var header = document.getElementById('header');
    var crumbs = document.querySelector('#container > nav[aria-label="Breadcrumbs"]');
    var headerH = header ? header.offsetHeight : 0;
    var crumbsH = crumbs ? crumbs.offsetHeight : 0;
    var root = document.documentElement.style;
    root.setProperty('--admin-header-h', headerH + 'px');
    root.setProperty('--admin-sticky-h', (headerH + crumbsH) + 'px');
    root.setProperty('--admin-crumbs-h', crumbsH + 'px');
  }

  function init() {
    measure();
    var targets = [document.getElementById('header'), document.querySelector('#container > nav[aria-label="Breadcrumbs"]')]
      .filter(Boolean);
    if ('ResizeObserver' in window) {
      var observer = new ResizeObserver(measure);
      targets.forEach(function (el) { observer.observe(el); });
    } else {
      window.addEventListener('resize', measure);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
