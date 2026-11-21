/*
 * Admin list paging with a per-tab page cache.
 *
 * - The server only ever returns one page (System Configuration > Items Per Page, default 20).
 * - Clicking a page number fetches that page once, swaps the list in place and caches it in
 *   sessionStorage; going back to a page already seen uses the cache (no request).
 * - The cache is dropped when the tab is closed (sessionStorage), on logout, on the login
 *   page, and whenever a form is POSTed (save, delete, list action ...), so edits are never
 *   hidden behind stale pages.
 */
(function () {
  'use strict';

  var PREFIX = 'adminListCache:';
  var ORDER_KEY = PREFIX + '__order';
  var MAX_PAGES = 40;

  function storage() {
    try {
      var s = window.sessionStorage;
      s.getItem(ORDER_KEY);
      return s;
    } catch (err) {
      return null;
    }
  }

  function clearAll() {
    var s = storage();
    if (!s) return;
    try {
      for (var i = s.length - 1; i >= 0; i--) {
        var key = s.key(i);
        if (key && key.indexOf(PREFIX) === 0) s.removeItem(key);
      }
    } catch (err) { /* ignore */ }
  }

  function cacheKey(url) {
    return PREFIX + url.pathname + url.search;
  }

  function read(url) {
    var s = storage();
    if (!s) return null;
    try {
      var raw = s.getItem(cacheKey(url));
      return raw ? JSON.parse(raw) : null;
    } catch (err) {
      return null;
    }
  }

  function write(url, entry) {
    var s = storage();
    if (!s) return;
    var key = cacheKey(url);
    var order;
    try { order = JSON.parse(s.getItem(ORDER_KEY) || '[]'); } catch (err) { order = []; }
    order = order.filter(function (k) { return k !== key; });
    order.push(key);
    while (order.length > MAX_PAGES) s.removeItem(order.shift());
    for (var attempt = 0; attempt < 5; attempt++) {
      try {
        s.setItem(key, JSON.stringify(entry));
        s.setItem(ORDER_KEY, JSON.stringify(order));
        return;
      } catch (err) {
        // Quota exceeded: drop the oldest cached pages and retry.
        if (!order.length || order[0] === key) return;
        s.removeItem(order.shift());
      }
    }
  }

  // ---------------------------------------------------------------- clearing

  document.addEventListener('submit', function (event) {
    var form = event.target;
    if (form && (form.method || '').toLowerCase() === 'post') clearAll();
  }, true);

  document.addEventListener('click', function (event) {
    var link = event.target.closest && event.target.closest('a[href*="/logout/"]');
    if (link) clearAll();
  }, true);

  // ---------------------------------------------------------------- paging

  function snapshot() {
    var form = document.getElementById('changelist-form');
    return form ? { html: form.innerHTML, title: document.title } : null;
  }

  function reinit() {
    var boxes = document.querySelectorAll('tr input.action-select');
    if (boxes.length && typeof window.Actions === 'function') {
      try { window.Actions(boxes); } catch (err) { /* ignore */ }
    }
    document.dispatchEvent(new CustomEvent('admin:list-updated'));
  }

  function show(entry, url, push) {
    var form = document.getElementById('changelist-form');
    if (!form || !entry) return false;
    form.innerHTML = entry.html;
    if (entry.title) document.title = entry.title;
    if (push) history.pushState({ adminListCache: true }, '', url.href);
    reinit();
    var top = document.getElementById('changelist') || form;
    var rect = top.getBoundingClientRect();
    if (rect.top < 0) window.scrollTo({ top: window.scrollY + rect.top - 140, behavior: 'smooth' });
    return true;
  }

  function setBusy(on) {
    var form = document.getElementById('changelist-form');
    if (form) form.classList.toggle('list-page-loading', on);
  }

  function load(url, push) {
    var cached = read(url);
    if (cached && show(cached, url, push)) return;
    setBusy(true);
    fetch(url.href, { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (response) {
        if (!response.ok || response.redirected) throw new Error('reload');
        return response.text();
      })
      .then(function (html) {
        var doc = new DOMParser().parseFromString(html, 'text/html');
        var form = doc.getElementById('changelist-form');
        if (!form) throw new Error('reload');
        var entry = { html: form.innerHTML, title: doc.title };
        write(url, entry);
        setBusy(false);
        show(entry, url, push);
      })
      .catch(function () {
        // Session expired, error page, ... : fall back to a normal page load.
        window.location.href = url.href;
      });
  }

  function init() {
    if (document.body.classList.contains('login')) {
      clearAll();
      return;
    }
    var form = document.getElementById('changelist-form');
    if (!form || !document.body.classList.contains('change-list')) return;

    var here = new URL(window.location.href);
    write(here, snapshot());
    history.replaceState({ adminListCache: true }, '', here.href);

    // Capture phase: runs before the page-loader's link handler, which then sees
    // defaultPrevented and does not show the full-page overlay.
    document.addEventListener('click', function (event) {
      if (event.defaultPrevented || event.button !== 0) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      var link = event.target.closest && event.target.closest('#changelist-form .paginator a[href]');
      if (!link) return;
      var url = new URL(link.href, window.location.href);
      if (url.origin !== window.location.origin || url.pathname !== window.location.pathname) return;
      event.preventDefault();
      load(url, true);
    }, true);

    window.addEventListener('popstate', function (event) {
      if (!event.state || !event.state.adminListCache) return;
      var url = new URL(window.location.href);
      var cached = read(url);
      if (!cached || !show(cached, url, false)) window.location.reload();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
