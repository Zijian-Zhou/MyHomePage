(function () {
  function getLang() {
    var path = (window.location.pathname || '').toLowerCase();
    if (path.indexOf('/zh-hans/') === 0 || path.indexOf('/zh-cn/') === 0) return 'zh';
    return 'en';
  }

  function label() {
    return getLang() === 'zh' ? '\u4fdd\u5b58\u4e3a\u8349\u7a3f' : 'Save as draft';
  }

  document.addEventListener('DOMContentLoaded', function () {
    var draftField = document.getElementById('id_is_draft');
    var submitRow = document.querySelector('.submit-row');
    if (!draftField || !submitRow) return;

    var btn = document.createElement('input');
    btn.type = 'submit';
    btn.name = '_saveasdraft';
    btn.value = label();
    btn.className = 'default';
    btn.style.marginLeft = '8px';

    btn.addEventListener('click', function () {
      draftField.checked = true;
    });

    submitRow.appendChild(btn);
  });
})();
