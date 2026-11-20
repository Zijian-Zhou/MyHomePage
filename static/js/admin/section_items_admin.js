/*
 * Custom-section item editor (Section change form, stacked "items" inline).
 *
 * - Each item collapses/expands from its header; items start collapsed, except new
 *   ones and items with validation errors.
 * - The header shows the live title plus Detail / Draft / Inactive badges.
 * - Detail-content fields are shown only while "Enable Detail Page" is ticked.
 * - Every item gets its own Save (save and continue editing) and Delete buttons.
 */
(function () {
  'use strict';

  var GROUP_SELECTOR = '#items-group';

  function isZh() {
    return /^\/zh/i.test(window.location.pathname || '');
  }

  function t(key) {
    var zh = isZh();
    return {
      expand: zh ? '展开' : 'Expand',
      collapse: zh ? '收起' : 'Collapse',
      untitled: zh ? '（未命名）' : '(untitled)',
      detail: zh ? '详情页' : 'Detail page',
      draft: zh ? '草稿' : 'Draft',
      inactive: zh ? '未启用' : 'Inactive',
      save: zh ? '保存' : 'Save',
      del: zh ? '删除' : 'Delete',
      confirmDelete: zh ? '确定删除这个条目吗？删除后会立即保存页面。' : 'Delete this item? The page is saved right away.',
      confirmRemove: zh ? '移除这个尚未保存的条目吗？' : 'Remove this unsaved item?'
    }[key];
  }

  function field(item, suffix) {
    return item.querySelector('[name$="-' + suffix + '"]:not([type=hidden])');
  }

  function rows(item, names) {
    return names.map(function (name) {
      return item.querySelector('.form-row.field-' + name);
    }).filter(Boolean);
  }

  function setCollapsed(item, collapsed) {
    item.classList.toggle('si-collapsed', collapsed);
    var header = item.querySelector(':scope > h3');
    if (header) {
      header.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
      header.title = collapsed ? t('expand') : t('collapse');
    }
  }

  function refreshHeader(item) {
    var label = item.querySelector(':scope > h3 .si-title');
    var title = field(item, 'title');
    if (label) label.textContent = (title && title.value.trim()) || t('untitled');

    var badges = item.querySelector(':scope > h3 .si-badges');
    if (!badges) return;
    badges.innerHTML = '';
    function badge(cls, text) {
      var b = document.createElement('span');
      b.className = 'si-badge ' + cls;
      b.textContent = text;
      badges.appendChild(b);
    }
    var detail = field(item, 'enable_detail');
    var draft = field(item, 'is_draft');
    var active = field(item, 'is_active');
    if (detail && detail.checked) badge('si-badge-detail', t('detail'));
    if (draft && draft.checked) badge('si-badge-draft', t('draft'));
    if (active && !active.checked) badge('si-badge-inactive', t('inactive'));
  }

  function refreshDetailFields(item) {
    var detail = field(item, 'enable_detail');
    var show = !!(detail && detail.checked);
    rows(item, ['detail_content', 'detail_content_zh']).forEach(function (row) {
      row.classList.toggle('si-hidden', !show);
    });
  }

  function saveForm(item) {
    var form = item.closest('form');
    if (!form) return;
    var cont = form.querySelector('input[type=submit][name="_continue"]');
    if (cont) {
      cont.click();
    } else if (form.requestSubmit) {
      form.requestSubmit();
    } else {
      form.submit();
    }
  }

  function deleteItem(item) {
    var deleteBox = item.querySelector('input[type=checkbox][name$="-DELETE"]');
    if (deleteBox) {
      if (!window.confirm(t('confirmDelete'))) return;
      deleteBox.checked = true;
      saveForm(item);
      return;
    }
    // Unsaved form added with "Add another": let Django's formset remove it.
    if (!window.confirm(t('confirmRemove'))) return;
    var removeLink = item.querySelector('.inline-deletelink');
    if (removeLink) {
      removeLink.click();
    } else {
      item.remove();
    }
  }

  function enhance(item, expanded) {
    if (!item || item.dataset.siReady === '1' || item.classList.contains('empty-form')) return;
    if (item.id && /__prefix__/.test(item.id)) return;
    item.dataset.siReady = '1';
    item.classList.add('si-item');

    var header = item.querySelector(':scope > h3');
    if (header) {
      header.classList.add('si-header');
      header.setAttribute('role', 'button');
      header.setAttribute('tabindex', '0');
      var chevron = document.createElement('span');
      chevron.className = 'si-chevron';
      chevron.setAttribute('aria-hidden', 'true');
      header.insertBefore(chevron, header.firstChild);
      var title = document.createElement('span');
      title.className = 'si-title';
      var badges = document.createElement('span');
      badges.className = 'si-badges';
      // Django's own label ("#1" / object repr) is replaced by the live title.
      var original = header.querySelector('.inline_label');
      if (original) original.classList.add('si-original-label');
      header.insertBefore(title, chevron.nextSibling);
      header.appendChild(badges);

      header.addEventListener('click', function (event) {
        if (event.target.closest('a, input, label, button')) return;
        setCollapsed(item, !item.classList.contains('si-collapsed'));
      });
      header.addEventListener('keydown', function (event) {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          setCollapsed(item, !item.classList.contains('si-collapsed'));
        }
      });
    }

    var actions = document.createElement('div');
    actions.className = 'si-actions';
    var saveBtn = document.createElement('button');
    saveBtn.type = 'button';
    saveBtn.className = 'button si-save';
    saveBtn.textContent = t('save');
    saveBtn.addEventListener('click', function () { saveForm(item); });
    var delBtn = document.createElement('button');
    delBtn.type = 'button';
    delBtn.className = 'button si-delete';
    delBtn.textContent = t('del');
    delBtn.addEventListener('click', function () { deleteItem(item); });
    actions.appendChild(saveBtn);
    actions.appendChild(delBtn);
    item.appendChild(actions);

    ['title', 'enable_detail', 'is_draft', 'is_active'].forEach(function (name) {
      var input = field(item, name);
      if (!input) return;
      input.addEventListener(input.type === 'checkbox' ? 'change' : 'input', function () {
        refreshHeader(item);
        if (name === 'enable_detail') refreshDetailFields(item);
      });
    });

    refreshHeader(item);
    refreshDetailFields(item);
    var hasErrors = !!item.querySelector('.errorlist, .errors');
    setCollapsed(item, !(expanded || hasErrors));
  }

  function init() {
    var group = document.querySelector(GROUP_SELECTOR);
    if (!group) return;
    group.classList.add('si-enhanced');
    group.querySelectorAll('.inline-related').forEach(function (item) { enhance(item, false); });
  }

  document.addEventListener('DOMContentLoaded', init);

  // New forms from "Add another" start expanded so they can be filled in.
  document.addEventListener('formset:added', function (event) {
    var item = event.target;
    if (!item || !item.closest || !item.closest(GROUP_SELECTOR)) return;
    enhance(item, true);
    var title = field(item, 'title');
    if (title) title.focus();
  });
})();
