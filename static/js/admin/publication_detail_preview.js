(function () {
  function isZh() {
    return /^\/zh/i.test(window.location.pathname || '');
  }

  const msg = {
    preview: isZh() ? '\u9884\u89c8' : 'Preview',
    aiGenerate: isZh() ? 'AI \u751f\u6210' : 'AI Generate',
    rendering: isZh() ? '\u751f\u6210\u4e2d...' : 'Rendering...',
    checking: isZh() ? '\u6b63\u5728\u68c0\u67e5\u53ef\u7528 LLM API...' : 'Checking available LLM APIs...',
    selectProvider: isZh() ? '\u9009\u62e9 LLM API' : 'Select LLM API',
    noProvider: isZh() ? '\u6ca1\u6709\u53ef\u7528\u7684 LLM API\u3002' : 'No available LLM API.',
    generating: isZh() ? '\u6b63\u5728\u8bfb\u53d6\u8bba\u6587\u5143\u6570\u636e\u548c\u6587\u4ef6\u5185\u5bb9\uff0c\u5e76\u8c03\u7528 LLM \u751f\u6210...' : 'Reading metadata/files and generating with LLM...',
    saved: isZh() ? '\u5df2\u4fdd\u5b58\u5230\u8be6\u60c5\u5185\u5bb9\u5b57\u6bb5\u3002' : 'Saved to detail fields.',
    save: isZh() ? '\u6ee1\u610f\uff0c\u4fdd\u5b58' : 'Looks good, save',
    saveAfterEditing: isZh() ? '\u7f16\u8f91\u540e\u4fdd\u5b58' : 'Save After Editing',
    editTitle: isZh() ? '\u7f16\u8f91 AI \u751f\u6210\u7ed3\u679c' : 'Edit AI Result',
    saveEdited: isZh() ? '\u4fdd\u5b58\u7f16\u8f91\u7ed3\u679c' : 'Save Edited Result',
    revise: isZh() ? '\u4e0d\u6ee1\u610f\uff0c\u6309\u610f\u89c1\u4fee\u6539' : 'Revise with feedback',
    feedbackPlaceholder: isZh() ? '\u8f93\u5165\u4fee\u6539\u610f\u89c1\uff0c\u4f8b\u5982\uff1a\u66f4\u7a81\u51fa\u65b9\u6cd5\u8d21\u732e\uff0c\u51cf\u5c11\u80cc\u666f\u7bc7\u5e45\u3002' : 'Enter feedback, e.g. emphasize contributions and shorten background.',
    close: isZh() ? '\u5173\u95ed' : 'Close',
    needsSaved: isZh() ? '\u8bf7\u5148\u4fdd\u5b58\u8be5\u8bba\u6587\u6761\u76ee\uff0c\u7136\u540e\u518d\u4f7f\u7528 AI \u751f\u6210\u3002' : 'Save this publication first, then use AI generation.',
    failed: isZh() ? '\u64cd\u4f5c\u5931\u8d25' : 'Operation failed',
    en: 'English',
    zh: '\u4e2d\u6587'
  };

  function csrfToken() {
    const field = document.querySelector("input[name='csrfmiddlewaretoken']");
    if (field && field.value) return field.value;
    const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  function adminPublicationUrl(action) {
    const match = (window.location.pathname || '').match(/^(.*\/publication\/)([^/]+)\/change\/?$/);
    if (!match) return '';
    return match[1] + match[2] + '/' + action + '/';
  }

  function previewUrl() {
    const marker = '/publication/';
    const path = window.location.pathname;
    const idx = path.indexOf(marker);
    if (idx < 0) return '';
    return path.slice(0, idx + marker.length) + 'preview-detail/';
  }

  function postJson(url, payload) {
    return fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken()
      },
      body: JSON.stringify(payload || {})
    }).then(function (response) {
      return response.json().then(function (data) {
        if (!response.ok) throw new Error(data.error || data.detail || response.statusText || msg.failed);
        return data;
      });
    });
  }

  function postForm(url, payload) {
    const body = new URLSearchParams();
    Object.keys(payload || {}).forEach(function (key) { body.append(key, payload[key]); });
    return fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'X-CSRFToken': csrfToken()
      },
      body: body.toString()
    }).then(function (response) {
      return response.json().then(function (data) {
        if (!response.ok) throw new Error(data.error || data.detail || response.statusText || msg.failed);
        return data;
      });
    });
  }

  function fieldValue(id) {
    const el = document.getElementById(id);
    return el ? el.value || '' : '';
  }

  function metadataFromForm() {
    return {
      title: fieldValue('id_title'),
      authors: fieldValue('id_authors'),
      journal: fieldValue('id_journal'),
      year: fieldValue('id_year'),
      date: fieldValue('id_date'),
      doi: fieldValue('id_doi'),
      url: fieldValue('id_url'),
      keywords: fieldValue('id_keywords'),
      raw_bibtex: fieldValue('id_raw_bibtex')
    };
  }

  function ensureModal() {
    let mask = document.getElementById('publication-ai-detail-mask');
    if (mask) return mask;
    mask = document.createElement('div');
    mask.id = 'publication-ai-detail-mask';
    mask.className = 'publication-detail-preview-mask';
    mask.innerHTML = [
      '<div class="publication-detail-preview-panel publication-ai-detail-panel">',
      '<div class="publication-detail-preview-head">',
      '<h3>' + (isZh() ? 'AI \u8bba\u6587\u8be6\u60c5\u751f\u6210' : 'AI Publication Detail Generation') + '</h3>',
      '<button type="button" class="publication-detail-preview-close" aria-label="Close">&times;</button>',
      '</div>',
      '<div class="publication-ai-status"></div>',
      '<div class="publication-ai-provider-row" style="display:none;">',
      '<label>' + msg.selectProvider + '</label>',
      '<select class="publication-ai-provider-select"></select>',
      '<button type="button" class="button publication-ai-start-btn">' + msg.aiGenerate + '</button>',
      '</div>',
      '<div class="publication-ai-preview" style="display:none;">',
      '<div class="publication-ai-preview-grid">',
      '<div><h4>' + msg.en + '</h4><div class="publication-ai-preview-en publication-detail-preview-body"></div></div>',
      '<div><h4>' + msg.zh + '</h4><div class="publication-ai-preview-zh publication-detail-preview-body"></div></div>',
      '</div>',
      '<textarea class="publication-ai-feedback" placeholder="' + msg.feedbackPlaceholder + '"></textarea>',
      '<div class="publication-ai-actions">',
      '<button type="button" class="button publication-ai-save-btn">' + msg.save + '</button>',
      '<button type="button" class="button publication-ai-edit-save-btn">' + msg.saveAfterEditing + '</button>',
      '<button type="button" class="button publication-ai-revise-btn">' + msg.revise + '</button>',
      '</div>',
      '</div>',
      '</div>'
    ].join('');
    document.body.appendChild(mask);
    mask.addEventListener('click', function (event) {
      if (event.target === mask || event.target.classList.contains('publication-detail-preview-close')) {
        mask.style.display = 'none';
      }
    });
    return mask;
  }

  function ensurePlainPreviewModal() {
    let mask = document.getElementById('publication-plain-preview-mask');
    if (mask) return mask;
    mask = document.createElement('div');
    mask.id = 'publication-plain-preview-mask';
    mask.className = 'publication-detail-preview-mask';
    mask.innerHTML = [
      '<div class="publication-detail-preview-panel">',
      '<div class="publication-detail-preview-head">',
      '<h3>' + (isZh() ? '\u8be6\u60c5\u5185\u5bb9\u9884\u89c8' : 'Detail Content Preview') + '</h3>',
      '<button type="button" class="publication-detail-preview-close" aria-label="Close">&times;</button>',
      '</div>',
      '<div class="publication-plain-preview-body publication-detail-preview-body"></div>',
      '</div>'
    ].join('');
    document.body.appendChild(mask);
    mask.addEventListener('click', function (event) {
      if (event.target === mask || event.target.classList.contains('publication-detail-preview-close')) {
        mask.style.display = 'none';
      }
    });
    return mask;
  }

  function ensureEditModal() {
    let mask = document.getElementById('publication-ai-edit-mask');
    if (mask) return mask;
    mask = document.createElement('div');
    mask.id = 'publication-ai-edit-mask';
    mask.className = 'publication-detail-preview-mask';
    mask.innerHTML = [
      '<div class="publication-detail-preview-panel publication-ai-edit-panel">',
      '<div class="publication-detail-preview-head">',
      '<h3>' + msg.editTitle + '</h3>',
      '<button type="button" class="publication-detail-preview-close" aria-label="Close">&times;</button>',
      '</div>',
      '<div class="publication-ai-edit-grid">',
      '<label>' + msg.en + '<textarea class="publication-ai-edit-en"></textarea></label>',
      '<label>' + msg.zh + '<textarea class="publication-ai-edit-zh"></textarea></label>',
      '</div>',
      '<div class="publication-ai-actions publication-ai-edit-actions">',
      '<button type="button" class="button publication-ai-edit-confirm-btn">' + msg.saveEdited + '</button>',
      '</div>',
      '</div>'
    ].join('');
    document.body.appendChild(mask);
    mask.addEventListener('click', function (event) {
      if (event.target === mask || event.target.classList.contains('publication-detail-preview-close')) {
        mask.style.display = 'none';
      }
    });
    return mask;
  }

  function setStatus(mask, text, isError) {
    const status = mask.querySelector('.publication-ai-status');
    status.textContent = text || '';
    status.classList.toggle('is-error', !!isError);
  }

  function closeAiDetailModals() {
    ['publication-ai-detail-mask', 'publication-ai-edit-mask'].forEach(function (id) {
      const modal = document.getElementById(id);
      if (modal) modal.style.display = 'none';
    });
  }

  function setGenerated(mask, data) {
    mask._generated = {
      detail_content: data.detail_content || '',
      detail_content_zh: data.detail_content_zh || ''
    };
    mask.querySelector('.publication-ai-preview-en').innerHTML = data.html || '<p class="empty">No content</p>';
    mask.querySelector('.publication-ai-preview-zh').innerHTML = data.html_zh || '<p class="empty">\u6682\u65e0\u5185\u5bb9</p>';
    mask.querySelector('.publication-ai-preview').style.display = 'block';
  }

  function selectedProviderId(mask) {
    return mask.querySelector('.publication-ai-provider-select').value;
  }

  function generateWithProvider(mask, feedback) {
    const url = adminPublicationUrl('generate-detail');
    const providerRow = mask.querySelector('.publication-ai-provider-row');
    setStatus(mask, msg.generating, false);
    if (providerRow) providerRow.style.display = 'none';
    mask.querySelector('.publication-ai-preview').style.display = 'none';
    return postJson(url, {
      provider_id: selectedProviderId(mask),
      metadata: metadataFromForm(),
      feedback: feedback || '',
      previous: mask._generated || {}
    }).then(function (data) {
      setStatus(mask, '', false);
      setGenerated(mask, data);
      const feedbackEl = mask.querySelector('.publication-ai-feedback');
      if (feedbackEl) feedbackEl.value = '';
    }).catch(function (error) {
      if (providerRow) providerRow.style.display = 'flex';
      setStatus(mask, error.message || msg.failed, true);
    });
  }

  function startAiFlow() {
    const providersUrl = adminPublicationUrl('ai-providers');
    if (!providersUrl) {
      alert(msg.needsSaved);
      return;
    }
    const mask = ensureModal();
    mask.style.display = 'flex';
    mask._generated = null;
    mask.querySelector('.publication-ai-provider-row').style.display = 'none';
    mask.querySelector('.publication-ai-preview').style.display = 'none';
    setStatus(mask, msg.checking, false);

    fetch(providersUrl, { credentials: 'same-origin' })
      .then(function (response) {
        return response.json().then(function (data) {
          if (!response.ok) throw new Error(data.error || response.statusText || msg.failed);
          return data;
        });
      })
      .then(function (data) {
        const providers = data.providers || [];
        if (!providers.length) {
          setStatus(mask, msg.noProvider, true);
          return;
        }
        const select = mask.querySelector('.publication-ai-provider-select');
        select.innerHTML = '';
        providers.forEach(function (provider) {
          const option = document.createElement('option');
          option.value = provider.id;
          option.textContent = provider.name + ' (' + provider.provider + '/' + provider.model_name + ')' + (provider.is_default ? ' *' : '');
          select.appendChild(option);
        });
        setStatus(mask, '', false);
        mask.querySelector('.publication-ai-provider-row').style.display = 'flex';
      })
      .catch(function (error) {
        setStatus(mask, error.message || msg.failed, true);
      });

    mask.querySelector('.publication-ai-start-btn').onclick = function () {
      generateWithProvider(mask, '');
    };
    mask.querySelector('.publication-ai-revise-btn').onclick = function () {
      const feedback = mask.querySelector('.publication-ai-feedback').value || '';
      generateWithProvider(mask, feedback);
    };
    mask.querySelector('.publication-ai-save-btn').onclick = function () {
      if (!mask._generated) return;
      saveGenerated(mask, mask._generated);
    };
    mask.querySelector('.publication-ai-edit-save-btn').onclick = function () {
      if (!mask._generated) return;
      openEditModal(mask, mask._generated);
    };
  }

  function saveGenerated(mask, data) {
    setStatus(mask, isZh() ? '\u6b63\u5728\u4fdd\u5b58...' : 'Saving...', false);
    return postJson(adminPublicationUrl('save-detail'), data)
      .then(function () {
        const enField = document.getElementById('id_detail_content');
        const zhField = document.getElementById('id_detail_content_zh');
        const enableField = document.getElementById('id_enable_detail');
        if (enField) enField.value = data.detail_content || '';
        if (zhField) zhField.value = data.detail_content_zh || '';
        if (enableField) enableField.checked = true;
        mask._generated = {
          detail_content: data.detail_content || '',
          detail_content_zh: data.detail_content_zh || ''
        };
        setStatus(mask, msg.saved, false);
        closeAiDetailModals();
      })
      .catch(function (error) {
        setStatus(mask, error.message || msg.failed, true);
      });
  }

  function openEditModal(aiMask, generated) {
    const editMask = ensureEditModal();
    editMask.querySelector('.publication-ai-edit-en').value = generated.detail_content || '';
    editMask.querySelector('.publication-ai-edit-zh').value = generated.detail_content_zh || '';
    editMask.style.display = 'flex';
    editMask.querySelector('.publication-ai-edit-confirm-btn').onclick = function () {
      const edited = {
        detail_content: editMask.querySelector('.publication-ai-edit-en').value || '',
        detail_content_zh: editMask.querySelector('.publication-ai-edit-zh').value || ''
      };
      saveGenerated(aiMask, edited);
    };
  }

  function previewField(textarea, button) {
    const url = previewUrl();
    if (!url) return;
    button.disabled = true;
    const oldText = button.textContent;
    button.textContent = msg.rendering;
    postForm(url, { content: textarea.value || '' })
      .then(function (data) {
        const mask = ensurePlainPreviewModal();
        mask.style.display = 'flex';
        mask.querySelector('.publication-plain-preview-body').innerHTML = data.html || '<p class="empty">No content</p>';
      })
      .catch(function (error) {
        const mask = ensurePlainPreviewModal();
        mask.style.display = 'flex';
        mask.querySelector('.publication-plain-preview-body').textContent = error.message || msg.failed;
      })
      .finally(function () {
        button.disabled = false;
        button.textContent = oldText;
      });
  }

  function ensureActionRow(textarea) {
    if (!textarea || textarea.dataset.previewReady) return;
    textarea.dataset.previewReady = '1';

    const row = document.createElement('div');
    row.className = 'publication-detail-action-row';

    const control = textarea.parentNode ? textarea.parentNode.querySelector('.auto-translate-control') : null;
    if (control) row.appendChild(control);

    const previewButton = document.createElement('button');
    previewButton.type = 'button';
    previewButton.className = 'button publication-detail-preview-button';
    previewButton.textContent = msg.preview;
    previewButton.addEventListener('click', function () { previewField(textarea, previewButton); });
    row.appendChild(previewButton);

    const aiButton = document.createElement('button');
    aiButton.type = 'button';
    aiButton.className = 'button publication-detail-ai-button';
    aiButton.textContent = msg.aiGenerate;
    aiButton.addEventListener('click', startAiFlow);
    row.appendChild(aiButton);

    textarea.insertAdjacentElement('afterend', row);
  }

  document.addEventListener('DOMContentLoaded', function () {
    window.setTimeout(function () {
      ensureActionRow(document.getElementById('id_detail_content'));
      ensureActionRow(document.getElementById('id_detail_content_zh'));
    }, 0);
  });
})();
