/*
 * File manager page (Media Files changelist, templates/admin/myHomePage/mediafile/file_manager.html).
 * Every change posts the hidden action form, so the server stays the single place that
 * validates paths and permissions; this script only collects input and confirmations.
 */
(function () {
  'use strict';

  var root = document.querySelector('[data-file-manager]');
  if (!root) return;

  function readJson(id, fallback) {
    var node = document.getElementById(id);
    if (!node) return fallback;
    try { return JSON.parse(node.textContent); } catch (err) { return fallback; }
  }

  var L = readJson('file-manager-labels', {});
  var FOLDERS = readJson('file-manager-folders', []);
  var FILES = readJson('file-manager-files', {});
  var TEXT_PREVIEW_MAX_BYTES = 1024 * 1024;
  var TEXT_PREVIEW_MAX_CHARS = 200000;
  var actionForm = root.querySelector('[data-fm-action-form]');

  function displayFolder(path) {
    return path.replace(/^markdown_assets/, L.uploads_label || 'Uploads');
  }

  function lines(value) {
    return (value || '').split('\n').map(function (s) { return s.trim(); }).filter(Boolean);
  }

  // ------------------------------------------------------------------ dialog

  var dialog;

  function buildDialog() {
    dialog = document.createElement('div');
    dialog.className = 'fm-dialog-mask';
    dialog.hidden = true;
    dialog.innerHTML = [
      '<div class="fm-dialog" role="dialog" aria-modal="true" aria-labelledby="fm-dialog-title">',
      '<h2 id="fm-dialog-title"></h2>',
      '<p class="fm-dialog-message"></p>',
      '<ul class="fm-dialog-list"></ul>',
      '<label class="fm-dialog-field"><span></span><input type="text" autocomplete="off"></label>',
      '<label class="fm-dialog-field fm-dialog-select"><span></span><select></select></label>',
      '<div class="fm-dialog-actions">',
      '<button type="button" class="button fm-secondary" data-cancel></button>',
      '<button type="button" class="button" data-ok></button>',
      '</div></div>'
    ].join('');
    root.appendChild(dialog);  // inside #container so the admin button theme applies
  }

  function ask(options) {
    if (!dialog) buildDialog();
    return new Promise(function (resolve) {
      var box = dialog.querySelector('.fm-dialog');
      var title = dialog.querySelector('h2');
      var message = dialog.querySelector('.fm-dialog-message');
      var list = dialog.querySelector('.fm-dialog-list');
      var inputWrap = dialog.querySelector('.fm-dialog-field:not(.fm-dialog-select)');
      var input = inputWrap.querySelector('input');
      var selectWrap = dialog.querySelector('.fm-dialog-select');
      var select = selectWrap.querySelector('select');
      var ok = dialog.querySelector('[data-ok]');
      var cancel = dialog.querySelector('[data-cancel]');

      title.textContent = options.title || '';
      message.textContent = options.message || '';
      message.hidden = !options.message;
      list.innerHTML = '';
      (options.list || []).forEach(function (item) {
        var li = document.createElement('li');
        li.textContent = item;
        list.appendChild(li);
      });
      list.hidden = !(options.list && options.list.length);

      inputWrap.hidden = !options.input;
      if (options.input) {
        inputWrap.querySelector('span').textContent = options.input.label || '';
        input.value = options.input.value || '';
      }
      selectWrap.hidden = !options.select;
      if (options.select) {
        selectWrap.querySelector('span').textContent = options.select.label || '';
        select.innerHTML = '';
        options.select.options.forEach(function (opt) {
          var o = document.createElement('option');
          o.value = opt.value;
          o.textContent = opt.text;
          select.appendChild(o);
        });
      }
      ok.textContent = options.okText || L.ok || 'OK';
      ok.classList.toggle('fm-danger', !!options.danger);
      cancel.textContent = L.cancel || 'Cancel';
      dialog.hidden = false;

      function close(result) {
        dialog.hidden = true;
        ok.removeEventListener('click', onOk);
        cancel.removeEventListener('click', onCancel);
        dialog.removeEventListener('mousedown', onMask);
        document.removeEventListener('keydown', onKey, true);
        resolve(result);
      }
      function onOk() {
        if (options.input) {
          var value = input.value.trim();
          if (!value) { input.focus(); return; }
          close(value);
        } else if (options.select) {
          close(select.value);
        } else {
          close(true);
        }
      }
      function onCancel() { close(null); }
      function onMask(event) { if (!box.contains(event.target)) close(null); }
      function onKey(event) {
        if (event.key === 'Escape') { event.preventDefault(); close(null); }
        if (event.key === 'Enter' && event.target.tagName !== 'BUTTON') { event.preventDefault(); onOk(); }
      }
      ok.addEventListener('click', onOk);
      cancel.addEventListener('click', onCancel);
      dialog.addEventListener('mousedown', onMask);
      document.addEventListener('keydown', onKey, true);

      window.setTimeout(function () {
        if (options.input) {
          input.focus();
          var dot = input.value.lastIndexOf('.');
          input.setSelectionRange(0, options.input.keepExtension && dot > 0 ? dot : input.value.length);
        } else if (options.select) {
          select.focus();
        } else {
          ok.focus();
        }
      }, 0);
    });
  }

  // ------------------------------------------------------------------ submit

  function submit(fields, paths) {
    ['action', 'path', 'name', 'dest', 'force', 'title', 'is_active', 'is_draft'].forEach(function (name) {
      actionForm.elements[name].value = fields[name] || '';
    });
    if (fields.folder !== undefined) actionForm.elements.folder.value = fields.folder;
    var holder = actionForm.querySelector('[data-fm-paths]');
    holder.innerHTML = '';
    (paths || []).forEach(function (path) {
      var input = document.createElement('input');
      input.type = 'hidden';
      input.name = 'paths';
      input.value = path;
      holder.appendChild(input);
    });
    if (actionForm.requestSubmit) {
      actionForm.requestSubmit();
    } else {
      actionForm.submit();
    }
  }

  function rowOf(el) {
    return el.closest('tr[data-path]');
  }

  // ------------------------------------------------------------------ actions

  root.addEventListener('click', function (event) {
    var thumb = event.target.closest('.fm-thumb');
    if (thumb && rowOf(thumb)) {
      event.preventDefault();
      openPreview(FILES[rowOf(thumb).getAttribute('data-path')]);
      return;
    }
    var button = event.target.closest('button');
    if (!button || !root.contains(button)) return;
    var row = rowOf(button);
    if (button.hasAttribute('data-fm-more')) {
      toggleMenu(button);
      return;
    }
    closeMenus();

    if (button.hasAttribute('data-fm-preview') && row) {
      openPreview(FILES[row.getAttribute('data-path')]);
    } else if (button.hasAttribute('data-fm-edit') && row) {
      openEdit(FILES[row.getAttribute('data-path')], button.getAttribute('data-fm-edit') !== 'info', row);
    } else if (button.hasAttribute('data-fm-copy')) {
      var text = button.getAttribute('data-fm-copy');
      if (button.hasAttribute('data-fm-absolute')) text = new URL(text, window.location.origin).href;
      copy(text, button);
    } else if (button.hasAttribute('data-fm-new-folder')) {
      ask({ title: L.new_folder, input: { label: L.folder_name, value: '' } }).then(function (name) {
        if (name) submit({ action: 'mkdir', name: name });
      });
    } else if (button.hasAttribute('data-fm-upload-trigger')) {
      var fileInput = root.querySelector('[data-fm-file-input]');
      if (fileInput) fileInput.click();
    } else if (button.hasAttribute('data-fm-rename') && row) {
      var isDir = row.hasAttribute('data-dir');
      ask({
        title: L.rename,
        message: lines(row.getAttribute('data-path-links')).length ? L.confirm_move_links : '',
        list: lines(row.getAttribute('data-path-links')),
        input: { label: L.new_name, value: row.getAttribute('data-name'), keepExtension: !isDir }
      }).then(function (name) {
        if (name && name !== row.getAttribute('data-name')) {
          submit({ action: 'rename', path: row.getAttribute('data-path'), name: name, force: '1' });
        }
      });
    } else if (button.hasAttribute('data-fm-move') && row) {
      var path = row.getAttribute('data-path');
      var parent = path.slice(0, path.lastIndexOf('/'));
      var targets = FOLDERS.filter(function (folder) {
        return folder !== parent && folder !== path && folder.indexOf(path + '/') !== 0;
      });
      if (!targets.length) return;
      ask({
        title: L.move,
        message: lines(row.getAttribute('data-path-links')).length ? L.confirm_move_links : '',
        list: lines(row.getAttribute('data-path-links')),
        select: {
          label: L.move_to,
          options: targets.map(function (folder) { return { value: folder, text: displayFolder(folder) }; })
        }
      }).then(function (dest) {
        if (dest) submit({ action: 'move', path: path, dest: dest, force: '1' });
      });
    } else if (button.hasAttribute('data-fm-register') && row) {
      submit({ action: 'register', path: row.getAttribute('data-path') });
    } else if (button.hasAttribute('data-fm-delete') && row) {
      confirmDelete([row]);
    } else if (button.hasAttribute('data-fm-bulk-delete')) {
      var rows = selected().map(function (box) { return rowOf(box); }).filter(Boolean);
      if (rows.length) confirmDelete(rows);
    }
  });

  function confirmDelete(rows) {
    var links = [];
    rows.forEach(function (row) {
      lines(row.getAttribute('data-links')).forEach(function (label) {
        if (links.indexOf(label) < 0) links.push(label);
      });
    });
    ask({
      title: L.delete || 'Delete',
      message: (L.confirm_delete || 'Delete {n} item(s)?').replace('{n}', rows.length) +
        (links.length ? ' ' + L.confirm_links : ''),
      list: links.slice(0, 10),
      okText: L.delete,
      danger: true
    }).then(function (ok) {
      if (!ok) return;
      submit({ action: 'delete', force: '1' }, rows.map(function (row) { return row.getAttribute('data-path'); }));
    });
  }

  function copy(text, button) {
    function done() {
      button.classList.add('is-copied');
      var original = button.getAttribute('title');
      button.setAttribute('title', L.copied || 'Copied');
      window.setTimeout(function () {
        button.classList.remove('is-copied');
        button.setAttribute('title', original);
      }, 1400);
    }
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text); done(); });
    } else {
      fallbackCopy(text);
      done();
    }
  }

  function fallbackCopy(text) {
    var area = document.createElement('textarea');
    area.value = text;
    area.setAttribute('readonly', '');
    area.style.cssText = 'position:fixed;top:-1000px;opacity:0;';
    document.body.appendChild(area);
    area.select();
    try { document.execCommand('copy'); } catch (err) { /* ignore */ }
    area.remove();
  }

  // ------------------------------------------------------------------ "more" menu

  function closeMenus() {
    root.querySelectorAll('.fm-menu:not([hidden])').forEach(function (menu) {
      menu.hidden = true;
      var trigger = menu.parentNode.querySelector('[data-fm-more]');
      if (trigger) trigger.setAttribute('aria-expanded', 'false');
    });
  }

  function toggleMenu(button) {
    var menu = button.parentNode.querySelector('.fm-menu');
    var open = menu.hidden;
    closeMenus();
    if (!open) return;
    menu.hidden = false;
    button.setAttribute('aria-expanded', 'true');
    // Fixed position: the table wrapper scrolls, so an absolute menu would be clipped.
    var rect = button.getBoundingClientRect();
    var width = menu.offsetWidth;
    var height = menu.offsetHeight;
    var top = rect.bottom + 4;
    if (top + height > window.innerHeight - 8) top = Math.max(8, rect.top - height - 4);
    menu.style.top = top + 'px';
    menu.style.left = Math.max(8, Math.min(rect.right - width, window.innerWidth - width - 8)) + 'px';
  }

  document.addEventListener('click', function (event) {
    if (!event.target.closest('.fm-more')) closeMenus();
  });
  window.addEventListener('scroll', closeMenus, true);
  window.addEventListener('resize', closeMenus);
  root.addEventListener('click', function (event) {
    if (event.target.closest('.fm-menu a')) closeMenus();
  });

  // ------------------------------------------------------------------ panel (preview / edit)

  var panel;

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function openPanel(title, wide) {
    if (!panel) {
      panel = el('div', 'fm-panel-mask');
      panel.innerHTML = '<div class="fm-panel" role="dialog" aria-modal="true">' +
        '<div class="fm-panel-head"><h2></h2><button type="button" class="fm-panel-close">&times;</button></div>' +
        '<div class="fm-panel-body"></div><div class="fm-panel-foot"></div></div>';
      root.appendChild(panel);
      panel.querySelector('.fm-panel-close').addEventListener('click', closePanel);
      panel.addEventListener('mousedown', function (event) {
        if (event.target === panel) closePanel();
      });
      document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && !event.defaultPrevented && panel && !panel.hidden) closePanel();
      });
    }
    panel.querySelector('.fm-panel').classList.toggle('is-wide', !!wide);
    panel.querySelector('h2').textContent = title;
    panel.querySelector('.fm-panel-close').setAttribute('aria-label', L.cancel || 'Close');
    var body = panel.querySelector('.fm-panel-body');
    var foot = panel.querySelector('.fm-panel-foot');
    body.innerHTML = '';
    foot.innerHTML = '';
    panel.hidden = false;
    return { body: body, foot: foot };
  }

  function closePanel() {
    if (!panel) return;
    panel.hidden = true;
    // Stop audio/video and drop the frame so nothing keeps playing or loading.
    panel.querySelector('.fm-panel-body').innerHTML = '';
  }

  function inlineUrl(meta) {
    return meta.raw_url + '&inline=1';
  }

  function downloadLink(meta) {
    var a = el('a', 'button fm-secondary');
    a.href = meta.raw_url;
    a.setAttribute('download', '');
    a.innerHTML = '<i class="fas fa-download" aria-hidden="true"></i> ';
    a.appendChild(document.createTextNode(L.download || 'Download'));
    return a;
  }

  function openPreview(meta) {
    if (!meta || !meta.preview) return;
    var parts = openPanel(meta.name, meta.preview === 'pdf' || meta.preview === 'text');
    var stage = el('div', 'fm-preview fm-preview-' + meta.preview);
    parts.body.appendChild(stage);
    var caption = el('div', 'fm-preview-caption', meta.ext + ' · ' + meta.size_label);
    parts.body.appendChild(caption);
    parts.foot.appendChild(downloadLink(meta));

    function fail(message) {
      stage.innerHTML = '';
      stage.appendChild(el('p', 'fm-preview-message', message || L.preview_failed));
    }

    if (meta.preview === 'image') {
      var img = el('img');
      img.alt = meta.name;
      img.onload = function () {
        caption.textContent = meta.ext + ' · ' + img.naturalWidth + ' × ' + img.naturalHeight + ' · ' + meta.size_label;
      };
      img.onerror = function () { fail(); };
      img.src = inlineUrl(meta);
      stage.appendChild(img);
    } else if (meta.preview === 'video' || meta.preview === 'audio') {
      var media = el(meta.preview);
      media.controls = true;
      media.preload = 'metadata';
      media.onerror = function () { fail(); };
      media.src = inlineUrl(meta);
      stage.appendChild(media);
    } else if (meta.preview === 'pdf') {
      var frame = el('iframe');
      frame.title = meta.name;
      frame.src = inlineUrl(meta);
      stage.appendChild(frame);
    } else if (meta.preview === 'text') {
      if (meta.size > TEXT_PREVIEW_MAX_BYTES) {
        fail(L.too_large);
        return;
      }
      stage.appendChild(el('p', 'fm-preview-message', L.loading));
      fetch(inlineUrl(meta), { credentials: 'same-origin' })
        .then(function (response) {
          if (!response.ok) throw new Error(response.status);
          return response.text();
        })
        .then(function (text) {
          stage.innerHTML = '';
          if (text.length > TEXT_PREVIEW_MAX_CHARS) {
            stage.appendChild(el('p', 'fm-preview-message', L.truncated));
            text = text.slice(0, TEXT_PREVIEW_MAX_CHARS);
          }
          stage.appendChild(el('pre', '', text));  // textContent: never rendered as HTML
        })
        .catch(function () { fail(); });
    }
  }

  function infoRow(list, label, value) {
    if (value === null || value === undefined || value === '') return null;
    var dt = el('dt', '', label);
    var dd = el('dd');
    if (value instanceof Node) {
      dd.appendChild(value);
    } else {
      dd.textContent = value;
    }
    list.appendChild(dt);
    list.appendChild(dd);
    return dd;
  }

  function openEdit(meta, canEdit, row) {
    if (!meta) return;
    var editable = canEdit && meta.editable;
    var parts = openPanel(editable ? (L.edit_title || 'Edit file') : meta.name, false);
    var layout = el('div', 'fm-edit');
    parts.body.appendChild(layout);

    var side = el('div', 'fm-edit-preview');
    if (meta.preview === 'image') {
      var img = el('img');
      img.alt = '';
      img.src = inlineUrl(meta);
      side.appendChild(img);
    } else {
      side.appendChild(el('span', 'fm-edit-ext', meta.ext || '?'));
    }
    if (meta.preview) {
      var previewBtn = el('button', 'button fm-secondary', L.preview || 'Preview');
      previewBtn.type = 'button';
      previewBtn.addEventListener('click', function () { openPreview(meta); });
      side.appendChild(previewBtn);
    }
    layout.appendChild(side);

    var main = el('div', 'fm-edit-main');
    layout.appendChild(main);
    var info = el('dl', 'fm-info');
    infoRow(info, L.info_path, meta.path);
    infoRow(info, L.info_type, meta.ext);
    infoRow(info, L.info_size, meta.size_label + ' (' + meta.size.toLocaleString() + ' B)');
    infoRow(info, L.info_modified, meta.modified);
    if (meta.preview === 'image') {
      var dims = infoRow(info, L.info_dimensions, '…');
      var probe = new Image();
      probe.onload = function () { dims.textContent = probe.naturalWidth + ' × ' + probe.naturalHeight + ' px'; };
      probe.onerror = function () { dims.textContent = '-'; };
      probe.src = inlineUrl(meta);
    }
    var used = el('div', 'fm-info-refs');
    if (meta.refs.length) {
      meta.refs.forEach(function (ref) {
        var line = el('div');
        if (ref.url) {
          var a = el('a', '', ref.label);
          a.href = ref.url;
          line.appendChild(a);
        } else {
          line.textContent = ref.label;
        }
        if (ref.via !== 'field') {
          line.appendChild(el('span', 'fm-muted', ' (' + (ref.via === 'path' ? L.linked_path : L.linked_key) + ')'));
        }
        used.appendChild(line);
      });
    } else {
      used.textContent = L.none || '-';
    }
    infoRow(info, L.info_used_by, used);
    if (meta.url) {
      var link = el('code', '', new URL(meta.url, window.location.origin).href);
      infoRow(info, L.info_link, link);
    }
    main.appendChild(info);

    if (!editable) {
      if (!meta.editable) {
        main.appendChild(el('p', 'fm-note', L.managed_note));
        if (meta.owner_url) {
          var open = el('a', 'button fm-secondary', L.open_record);
          open.href = meta.owner_url;
          parts.foot.appendChild(open);
        }
      }
      parts.foot.appendChild(downloadLink(meta));
      return;
    }

    var form = el('div', 'fm-edit-form');
    function field(label, input, hint) {
      var wrap = el('label', 'fm-form-field');
      wrap.appendChild(el('span', '', label));
      wrap.appendChild(input);
      if (hint) wrap.appendChild(el('small', 'fm-muted', hint));
      form.appendChild(wrap);
      return input;
    }
    function check(label, checked) {
      var wrap = el('label', 'fm-form-check');
      var box = el('input');
      box.type = 'checkbox';
      box.checked = !!checked;
      wrap.appendChild(box);
      wrap.appendChild(el('span', '', label));
      form.appendChild(wrap);
      return box;
    }
    var nameInput = el('input');
    nameInput.type = 'text';
    nameInput.maxLength = 150;
    nameInput.value = meta.name;
    field(L.file_name, nameInput);
    var titleInput = el('input');
    titleInput.type = 'text';
    titleInput.maxLength = 200;
    titleInput.value = meta.title || meta.name.replace(/\.[^.]+$/, '');
    field(L.title_label, titleInput, L.title_hint);
    var active = check(L.active_label, meta.is_active);
    var draft = check(L.draft_label, meta.is_draft);
    main.appendChild(form);

    var cancel = el('button', 'button fm-secondary', L.cancel);
    cancel.type = 'button';
    cancel.addEventListener('click', closePanel);
    var save = el('button', 'button', L.save || 'Save');
    save.type = 'button';
    parts.foot.appendChild(cancel);
    parts.foot.appendChild(save);

    function send() {
      submit({
        action: 'update', path: meta.path, name: nameInput.value.trim(), force: '1',
        title: titleInput.value.trim(), is_active: active.checked ? '1' : '', is_draft: draft.checked ? '1' : ''
      });
    }
    save.addEventListener('click', function () {
      var name = nameInput.value.trim();
      if (!name) { nameInput.focus(); return; }
      var pathLinks = lines(row && row.getAttribute('data-path-links'));
      if (name !== meta.name && pathLinks.length) {
        ask({ title: L.rename, message: L.confirm_move_links, list: pathLinks }).then(function (ok) {
          if (ok) send();
        });
      } else {
        send();
      }
    });
    form.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' && event.target.tagName === 'INPUT' && event.target.type === 'text') {
        event.preventDefault();
        save.click();
      }
    });
    window.setTimeout(function () {
      nameInput.focus();
      var dot = nameInput.value.lastIndexOf('.');
      nameInput.setSelectionRange(0, dot > 0 ? dot : nameInput.value.length);
    }, 0);
  }

  // ------------------------------------------------------------------ selection

  function selected() {
    return Array.prototype.slice.call(root.querySelectorAll('[data-fm-select]:checked'));
  }

  function refreshSelection() {
    var bar = root.querySelector('[data-fm-bulkbar]');
    var count = selected().length;
    if (bar) {
      bar.hidden = count === 0;
      var label = bar.querySelector('[data-fm-selected-count]');
      if (label) label.textContent = count + ' ' + (L.selected || 'selected');
    }
    var all = root.querySelector('[data-fm-select-all]');
    var boxes = root.querySelectorAll('[data-fm-select]');
    if (all) {
      all.checked = boxes.length > 0 && count === boxes.length;
      all.indeterminate = count > 0 && count < boxes.length;
      all.disabled = boxes.length === 0;
    }
  }

  root.addEventListener('change', function (event) {
    var target = event.target;
    if (target.matches('[data-fm-select-all]')) {
      root.querySelectorAll('[data-fm-select]').forEach(function (box) { box.checked = target.checked; });
      refreshSelection();
    } else if (target.matches('[data-fm-select]')) {
      refreshSelection();
    } else if (target.matches('[data-fm-autosubmit]')) {
      target.form.submit();
    } else if (target.matches('[data-fm-file-input]') && target.files.length) {
      target.form.requestSubmit ? target.form.requestSubmit() : target.form.submit();
    }
  });
  refreshSelection();

  // ------------------------------------------------------------------ drag & drop

  var dropzone = root.querySelector('[data-fm-dropzone]');
  if (dropzone) {
    var input = dropzone.querySelector('[data-fm-file-input]');
    ['dragenter', 'dragover'].forEach(function (type) {
      dropzone.addEventListener(type, function (event) {
        event.preventDefault();
        dropzone.classList.add('is-dragover');
      });
    });
    ['dragleave', 'dragend'].forEach(function (type) {
      dropzone.addEventListener(type, function () { dropzone.classList.remove('is-dragover'); });
    });
    dropzone.addEventListener('drop', function (event) {
      event.preventDefault();
      dropzone.classList.remove('is-dragover');
      if (!event.dataTransfer || !event.dataTransfer.files.length) return;
      input.files = event.dataTransfer.files;
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });
  }
})();
