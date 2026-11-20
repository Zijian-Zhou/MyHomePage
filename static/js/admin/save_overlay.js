(function () {
  'use strict';

  var submittingForm = null;

  function isChinese() {
    var language = (document.documentElement.lang || '').toLowerCase();
    return language.indexOf('zh') === 0 || /^\/zh(?:-hans|-cn)?\//.test(window.location.pathname);
  }

  function labels() {
    if (isChinese()) {
      return {
        title: '正在保存...',
        text: '请稍候，请勿关闭页面或重复提交。'
      };
    }
    return {
      title: 'Saving changes...',
      text: 'Please wait. Do not close the page or submit again.'
    };
  }

  function showOverlay(form) {
    var copy = labels();
    submittingForm = form;
    form.setAttribute('aria-busy', 'true');
    document.body.classList.add('admin-save-in-progress');
    if (window.PageLoader) {
      window.PageLoader.show({ title: copy.title, text: copy.text, immediate: true, persist: true });
    }
  }

  function hideOverlay() {
    if (submittingForm) {
      submittingForm.removeAttribute('aria-busy');
    }
    submittingForm = null;
    document.body.classList.remove('admin-save-in-progress');
    if (window.PageLoader) window.PageLoader.hide();
  }

  function isAdminSaveForm(form) {
    return document.body.classList.contains('change-form') &&
      form instanceof HTMLFormElement &&
      form.querySelector('.submit-row input[type="submit"], .submit-row button[type="submit"]');
  }

  document.addEventListener('submit', function (event) {
    var form = event.target;
    if (!isAdminSaveForm(form)) return;

    if (submittingForm) {
      event.preventDefault();
      return;
    }

    showOverlay(form);

    // Other form handlers may still cancel submission after this listener runs.
    window.setTimeout(function () {
      if (event.defaultPrevented) hideOverlay();
    }, 0);
  }, true);

  // A page restored from the back-forward cache must not retain the old overlay.
  window.addEventListener('pageshow', hideOverlay);
}());
