(function () {
  function readJsonScript(id) {
    var el = document.getElementById(id);
    if (!el) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      return null;
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    var categoryEl = document.getElementById("id_category");
    if (!categoryEl) return;

    var switchMap = readJsonScript("systemconfig-category-switch-map") || {};
    var currentCategory = readJsonScript("systemconfig-current-category") || "";
    if (!Object.keys(switchMap).length) return;

    categoryEl.addEventListener("change", function () {
      var selected = categoryEl.value;
      if (!selected || selected === currentCategory) return;
      if (switchMap[selected]) {
        window.location.href = switchMap[selected];
      }
    });
  });
})();
