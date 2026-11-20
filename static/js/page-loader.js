/*
 * Page loader controller (public site + admin).
 *
 *   window.PageLoader.show({ title, text, immediate, persist })
 *   window.PageLoader.hide()
 *
 * - The overlay is rendered in the HTML (templates/includes/page_loader.html) so a new
 *   page starts covered; it fades out once the DOM is ready.
 * - Same-origin link clicks and form submissions fade it in before the browser leaves,
 *   unless another script cancelled the event (AJAX pagination, modals, ...).
 * - Downloads, new-tab links and in-page anchors are ignored. Navigation overlays hide
 *   themselves after a while in case the browser never leaves (e.g. a download);
 *   explicit long operations pass persist: true.
 */
(function () {
  'use strict';

  var NAVIGATION_FAILSAFE_MS = 25000;
  var DOWNLOAD_PATH = /\/(download|publication-file|media-file)(\/|$)|\/media\/|\.(zip|pdf|bib|csv|json|txt|png|jpe?g|gif|webp|ico|svg|docx?|xlsx?|pptx?)$/i;
  var failsafeTimer = null;
  var defaults = null;

  function root() {
    return document.getElementById('page-loader');
  }

  function isZh() {
    var lang = (document.documentElement.lang || '').toLowerCase();
    return lang.indexOf('zh') === 0 || /^\/zh(-hans|-cn)?\//.test(window.location.pathname);
  }

  function rememberDefaults(el) {
    if (defaults || !el) return;
    defaults = {
      title: el.querySelector('.page-loader-title').textContent,
      text: el.querySelector('.page-loader-text').textContent
    };
  }

  var persistent = false;

  function show(options) {
    var el = root();
    if (!el) return;
    options = options || {};
    // An explicit long operation (sync, save, backup) already owns the overlay: a later
    // generic navigation call must not replace its text or give it a timeout, otherwise
    // the overlay disappears while the server is still working.
    if (persistent && el.classList.contains('is-visible') && !options.persist) return;
    persistent = !!options.persist;
    rememberDefaults(el);
    el.classList.remove('is-initial');
    el.querySelector('.page-loader-title').textContent = options.title || defaults.title;
    el.querySelector('.page-loader-text').textContent = options.text || '';
    el.classList.toggle('is-immediate', !!options.immediate);
    el.setAttribute('aria-hidden', 'false');
    el.classList.add('is-visible');
    document.documentElement.setAttribute('aria-busy', 'true');

    window.clearTimeout(failsafeTimer);
    if (!options.persist) {
      failsafeTimer = window.setTimeout(hide, NAVIGATION_FAILSAFE_MS);
    }
  }

  function hide() {
    var el = root();
    persistent = false;
    window.clearTimeout(failsafeTimer);
    document.documentElement.removeAttribute('aria-busy');
    if (!el) return;
    rememberDefaults(el);
    el.classList.remove('is-visible', 'is-immediate', 'is-initial');
    el.setAttribute('aria-hidden', 'true');
  }

  function isVisible() {
    var el = root();
    return !!el && el.classList.contains('is-visible') && !el.classList.contains('is-initial');
  }

  function leavesPage(url) {
    if (url.origin !== window.location.origin) return false;
    if (url.pathname === window.location.pathname && url.search === window.location.search) return false;
    return !DOWNLOAD_PATH.test(url.pathname);
  }

  function linkShouldShow(link, event) {
    if (event.defaultPrevented || event.button !== 0) return false;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return false;
    if (link.target && link.target !== '_self') return false;
    if (link.hasAttribute('download') || link.closest('[data-no-loader]')) return false;
    var href = link.getAttribute('href') || '';
    if (!href || href.charAt(0) === '#' || /^(javascript|mailto|tel):/i.test(href)) return false;
    try {
      return leavesPage(new URL(link.href, window.location.href));
    } catch (err) {
      return false;
    }
  }

  function formShouldShow(form) {
    if (!(form instanceof HTMLFormElement)) return false;
    if (form.target && form.target !== '_self') return false;
    if (form.closest('[data-no-loader]')) return false;
    return true;
  }

  document.addEventListener('click', function (event) {
    var link = event.target && event.target.closest ? event.target.closest('a[href]') : null;
    if (!link) return;
    // Decide after every other handler had a chance to call preventDefault().
    window.setTimeout(function () {
      if (linkShouldShow(link, event) && !isVisible()) show();
    }, 0);
  });

  document.addEventListener('submit', function (event) {
    var form = event.target;
    window.setTimeout(function () {
      if (event.defaultPrevented || !formShouldShow(form) || isVisible()) return;
      // POST submissions (admin actions, saves, sync selected...) can run longer than the
      // navigation failsafe and never trigger downloads here: keep the overlay until the
      // next page arrives.
      var isPost = (form.getAttribute('method') || 'get').toLowerCase() === 'post';
      show({ persist: isPost || form.hasAttribute('data-loader-persist') });
    }, 0);
  });

  // form.submit() (e.g. language selectors) does not fire a submit event.
  var nativeSubmit = HTMLFormElement.prototype.submit;
  HTMLFormElement.prototype.submit = function () {
    if (formShouldShow(this) && !isVisible()) show();
    return nativeSubmit.apply(this, arguments);
  };

  function revealPage() {
    hide();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', revealPage);
  } else {
    revealPage();
  }

  // Back/forward cache restores the old page with the overlay still showing.
  window.addEventListener('pageshow', function (event) {
    if (event.persisted) hide();
  });

  window.PageLoader = { show: show, hide: hide, isVisible: isVisible, isZh: isZh };
})();
