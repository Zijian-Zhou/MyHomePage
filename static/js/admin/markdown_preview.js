/*
 * Markdown preview buttons: custom-section item content (inline formsets) and any
 * textarea marked with data-markdown-preview (News / Research "Detail Content").
 *
 * Adds a "Preview" button under every `<prefix>-content` / `<prefix>-content_zh`
 * textarea of an inline formset, next to the Translate button when present, and shows
 * the server-rendered HTML (same renderer as the public site) in a modal. Inline forms
 * added later with "Add another" are handled through Django's `formset:added` event.
 */
(function () {
  'use strict';

  var FIELD_SELECTOR = [
    '.inline-group textarea[name$="-content"]',
    '.inline-group textarea[name$="-content_zh"]',
    '.inline-group textarea[name$="-detail_content"]',
    '.inline-group textarea[name$="-detail_content_zh"]',
    'textarea[data-markdown-preview]'  // e.g. News / Research "Detail Content"
  ].join(', ');

  function isZhPage() {
    return /^\/zh/i.test(window.location.pathname || '');
  }

  function text(key) {
    var zh = isZhPage();
    return {
      preview: zh ? '预览' : 'Preview',
      rendering: zh ? '正在生成…' : 'Rendering...',
      title: zh ? 'Markdown 预览' : 'Markdown Preview',
      close: zh ? '关闭' : 'Close',
      failed: zh ? '预览失败' : 'Preview failed',
      empty: zh ? '（内容为空）' : '(empty)'
    }[key];
  }

  function previewUrl() {
    var path = window.location.pathname || '';
    var index = path.indexOf('/admin/');
    return index < 0 ? '' : path.slice(0, index + '/admin/'.length) + 'markdown-preview/';
  }

  function csrfToken() {
    var field = document.querySelector("input[name='csrfmiddlewaretoken']");
    if (field && field.value) return field.value;
    var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  function ensureModal() {
    var mask = document.getElementById('markdown-preview-mask');
    if (mask) return mask;
    mask = document.createElement('div');
    mask.id = 'markdown-preview-mask';
    mask.className = 'publication-detail-preview-mask';
    mask.innerHTML = [
      '<div class="publication-detail-preview-panel" role="dialog" aria-modal="true">',
      '<div class="publication-detail-preview-head">',
      '<h3></h3>',
      '<button type="button" class="publication-detail-preview-close">&times;</button>',
      '</div>',
      '<div class="publication-detail-preview-body markdown-preview-body"></div>',
      '</div>'
    ].join('');
    mask.querySelector('h3').textContent = text('title');
    var close = mask.querySelector('.publication-detail-preview-close');
    close.setAttribute('aria-label', text('close'));
    function hide() { mask.style.display = 'none'; }
    close.addEventListener('click', hide);
    mask.addEventListener('click', function (event) {
      if (event.target === mask) hide();
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') hide();
    });
    document.body.appendChild(mask);
    return mask;
  }

  // Keep the action row in the same column as the textarea (see profile_bio_preview.js).
  function placeRowUnderField(textarea, row) {
    var column = document.createElement('div');
    column.className = 'field-with-actions';
    column.style.cssText = 'display:flex;flex-direction:column;align-items:flex-start;min-width:0;max-width:100%;flex:1 1 auto;';
    textarea.parentNode.insertBefore(column, textarea);
    column.appendChild(textarea);
    column.appendChild(row);
  }

  function render(textarea, button) {
    var endpoint = previewUrl();
    if (!endpoint) return;
    var original = button.textContent;
    button.disabled = true;
    button.textContent = text('rendering');
    var body = new URLSearchParams();
    body.append('content', textarea.value || '');
    fetch(endpoint, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'X-CSRFToken': csrfToken()
      },
      body: body.toString()
    })
      .then(function (response) {
        return response.json().catch(function () { return {}; }).then(function (data) {
          if (!response.ok) throw new Error(data.error || ('HTTP ' + response.status));
          return data;
        });
      })
      .then(function (data) {
        var mask = ensureModal();
        var target = mask.querySelector('.markdown-preview-body');
        if (data.html) {
          target.innerHTML = data.html;  // server output: Markdown with raw HTML escaped
        } else {
          target.textContent = text('empty');
        }
        mask.style.display = 'flex';
      })
      .catch(function (error) {
        window.alert(text('failed') + ': ' + (error.message || ''));
      })
      .then(function () {
        button.disabled = false;
        button.textContent = original;
      });
  }

  function addPreview(textarea) {
    if (!textarea || textarea.dataset.markdownPreviewReady === '1') return;
    if (/__prefix__/.test(textarea.name || '')) return;  // the hidden empty-form template
    textarea.dataset.markdownPreviewReady = '1';

    var row = document.createElement('div');
    row.className = 'publication-detail-action-row';
    var translateControl = textarea.parentNode ? textarea.parentNode.querySelector('.auto-translate-control') : null;
    if (translateControl) row.appendChild(translateControl);

    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'button publication-detail-preview-button';
    button.textContent = text('preview');
    button.addEventListener('click', function () { render(textarea, button); });
    row.appendChild(button);
    placeRowUnderField(textarea, row);
  }

  function scan(root) {
    (root || document).querySelectorAll(FIELD_SELECTOR).forEach(addPreview);
  }

  document.addEventListener('DOMContentLoaded', function () {
    window.setTimeout(function () { scan(document); }, 0);
  });

  // Django 4.1+ dispatches formset:added on the new form row.
  document.addEventListener('formset:added', function (event) {
    window.setTimeout(function () { scan(event.target); }, 0);
  });
})();
