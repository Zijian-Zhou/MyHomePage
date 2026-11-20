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

  function showOverlay() {
    if (window.PageLoader) {
      window.PageLoader.show({ title: t('title'), text: t('text'), immediate: true, persist: true });
    }
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
