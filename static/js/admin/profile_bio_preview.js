(function () {
  function isZhPage() {
    return /^\/zh/i.test(window.location.pathname || '');
  }

  function csrfToken() {
    var field = document.querySelector("input[name='csrfmiddlewaretoken']");
    if (field && field.value) return field.value;
    var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  function previewUrl() {
    var marker = '/profile/';
    var path = window.location.pathname || '';
    var index = path.indexOf(marker);
    if (index < 0) return '';
    return path.slice(0, index + marker.length) + 'preview-bio/';
  }

  function ensureModal() {
    var mask = document.getElementById('profile-bio-preview-mask');
    if (mask) return mask;
    mask = document.createElement('div');
    mask.id = 'profile-bio-preview-mask';
    mask.className = 'publication-detail-preview-mask';
    mask.innerHTML = [
      '<div class="publication-detail-preview-panel">',
      '<div class="publication-detail-preview-head">',
      '<h3>' + (isZhPage() ? '\u4e2a\u4eba\u7b80\u4ecb Markdown \u9884\u89c8' : 'Bio Markdown Preview') + '</h3>',
      '<button type="button" class="publication-detail-preview-close" aria-label="Close">&times;</button>',
      '</div>',
      '<div class="profile-bio-preview-body publication-detail-preview-body"></div>',
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

  function addPreview(textarea) {
    if (!textarea || textarea.dataset.bioPreviewReady === '1') return;
    textarea.dataset.bioPreviewReady = '1';

    var row = document.createElement('div');
    row.className = 'publication-detail-action-row';
    var translateControl = textarea.parentNode
      ? textarea.parentNode.querySelector('.auto-translate-control')
      : null;
    if (translateControl) row.appendChild(translateControl);

    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'button publication-detail-preview-button';
    button.textContent = isZhPage() ? '\u9884\u89c8' : 'Preview';
    button.addEventListener('click', function () {
      var endpoint = previewUrl();
      if (!endpoint) return;
      var original = button.textContent;
      button.disabled = true;
      button.textContent = isZhPage() ? '\u6b63\u5728\u751f\u6210...' : 'Rendering...';
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
          return response.json().then(function (data) {
            if (!response.ok) throw new Error(data.error || response.statusText);
            return data;
          });
        })
        .then(function (data) {
          var mask = ensureModal();
          mask.querySelector('.profile-bio-preview-body').innerHTML = data.html || '<p>--</p>';
          mask.style.display = 'flex';
        })
        .catch(function (error) {
          window.alert(error.message || (isZhPage() ? '\u9884\u89c8\u5931\u8d25' : 'Preview failed'));
        })
        .finally(function () {
          button.disabled = false;
          button.textContent = original;
        });
    });
    row.appendChild(button);
    textarea.insertAdjacentElement('afterend', row);
  }

  document.addEventListener('DOMContentLoaded', function () {
    window.setTimeout(function () {
      addPreview(document.getElementById('id_bio'));
      addPreview(document.getElementById('id_bio_zh'));
    }, 0);
  });
}());
