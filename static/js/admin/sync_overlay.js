document.addEventListener('DOMContentLoaded', function () {
  function getLang() {
    var path = window.location.pathname || '';
    return path.indexOf('/zh-hans/') === 0 ? 'zh-hans' : 'en';
  }

  function t(key) {
    var lang = getLang();
    var dict = {
      'zh-hans': {
        title: '正在同步...',
        text: '请稍候，请勿重复点击。'
      },
      en: {
        title: 'Synchronizing...',
        text: 'Please wait and do not click repeatedly.'
      }
    };
    return (dict[lang] && dict[lang][key]) || dict.en[key];
  }

  function ensureOverlay() {
    var overlay = document.getElementById('sync-progress-overlay');
    if (overlay) return overlay;

    overlay = document.createElement('div');
    overlay.id = 'sync-progress-overlay';
    overlay.className = 'sync-progress-overlay';
    overlay.style.display = 'none';
    overlay.innerHTML =
      '<div class="sync-progress-card">' +
      '<div class="sync-spinner" aria-hidden="true"></div>' +
      '<div class="sync-progress-title">' + t('title') + '</div>' +
      '<div class="sync-progress-text">' + t('text') + '</div>' +
      '</div>';
    document.body.appendChild(overlay);
    return overlay;
  }

  function showOverlay() {
    var overlay = ensureOverlay();
    overlay.style.display = 'flex';
  }

  function disableSyncButtons() {
    var buttons = document.querySelectorAll('a.sync-button');
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].classList.add('disabled');
      buttons[i].setAttribute('aria-disabled', 'true');
      buttons[i].style.pointerEvents = 'none';
    }
  }

  var syncButtons = document.querySelectorAll('a.sync-button');
  for (var i = 0; i < syncButtons.length; i++) {
    syncButtons[i].addEventListener('click', function (e) {
      if (this.classList.contains('disabled')) {
        e.preventDefault();
        return;
      }
      disableSyncButtons();
      showOverlay();
    });
  }
});
