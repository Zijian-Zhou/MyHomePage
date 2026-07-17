(function () {
  function detectLanguage() {
    var cookieMatch = document.cookie.match(/(?:^|;\s*)django_language=([^;]+)/);
    if (cookieMatch && cookieMatch[1]) {
      var cookieLang = decodeURIComponent(cookieMatch[1]).toLowerCase();
      if (cookieLang.indexOf("zh") === 0) return "zh";
      if (cookieLang.indexOf("en") === 0) return "en";
    }

    var path = (window.location.pathname || "").toLowerCase();
    if (path.indexOf("/zh-hans/") === 0 || path.indexOf("/zh-cn/") === 0) {
      return "zh";
    }
    if (path.indexOf("/en/") === 0) {
      return "en";
    }

    var htmlLang = (document.documentElement.lang || "").toLowerCase();
    if (htmlLang.indexOf("zh") === 0) {
      return "zh";
    }

    var langSelect = document.querySelector('select[name="language"]');
    if (langSelect && ((langSelect.value || "").toLowerCase().indexOf("zh") === 0)) {
      return "zh";
    }

    // Prefer Chinese as fallback to avoid showing English in zh-hans admin.
    return "zh";
  }

  function getMessage(key) {
    var isZh = detectLanguage() === "zh";
    var messages = {
      invalidJson: isZh
        ? "\u9875\u811a\u663e\u793a\u9879\u5fc5\u987b\u662f\u5408\u6cd5 JSON\u3002"
        : "Footer Items must be valid JSON.",
      invalidItem: isZh
        ? '\u9875\u811a\u663e\u793a\u9879\u5fc5\u987b\u5305\u542b "item"\uff08\u5bf9\u8c61\u6216\u6570\u7ec4\uff09\u3002'
        : 'Footer Items must contain "item" as an object or list.',
      invalidContent: isZh
        ? '\u6bcf\u4e2a item \u90fd\u5fc5\u987b\u5305\u542b\u975e\u7a7a "content"\u3002'
        : 'Each footer item must include a non-empty "content".'
    };
    return messages[key];
  }

  function parseFooterConfig(text) {
    var payload;
    try {
      payload = JSON.parse(text);
    } catch (e) {
      return getMessage("invalidJson");
    }

    var itemData = payload.item;
    if (itemData && !Array.isArray(itemData) && typeof itemData === "object") {
      itemData = [itemData];
    }
    if (!Array.isArray(itemData) || itemData.length === 0) {
      return getMessage("invalidItem");
    }

    for (var i = 0; i < itemData.length; i++) {
      var entry = itemData[i];
      if (!entry || typeof entry !== "object" || !String(entry.content || "").trim()) {
        return getMessage("invalidContent");
      }
    }
    return "";
  }

  function ensureErrorNode(form) {
    var list = document.getElementById("footer-json-messages");
    if (!list) {
      list = document.createElement("ul");
      list.id = "footer-json-messages";
      list.className = "messagelist";
      list.style.display = "none";
      var contentContainer = form.closest(".content") || document.querySelector(".content") || form.parentNode;
      contentContainer.insertBefore(list, form);
    }

    var item = document.getElementById("footer-json-error");
    if (item) return item;

    item = document.createElement("li");
    item.id = "footer-json-error";
    item.className = "error";
    list.appendChild(item);
    return item;
  }

  function isFooterCategory(categoryEl) {
    return categoryEl && categoryEl.value === "footer_items";
  }


  function validateAndShow(form, categoryEl, valueEl) {
    var errorNode = ensureErrorNode(form);
    var messageList = document.getElementById("footer-json-messages");
    if (!isFooterCategory(categoryEl)) {
      if (messageList) messageList.style.display = "none";
      errorNode.textContent = "";
      return true;
    }

    var raw = String((valueEl && valueEl.value) || "").trim();
    if (!raw) {
      if (messageList) messageList.style.display = "none";
      errorNode.textContent = "";
      return true;
    }

    var err = parseFooterConfig(raw);
    if (err) {
      errorNode.textContent = err;
      if (messageList) messageList.style.display = "block";
      return false;
    }

    if (messageList) messageList.style.display = "none";
    errorNode.textContent = "";
    return true;
  }

  document.addEventListener("DOMContentLoaded", function () {
    var form = document.querySelector("form");
    var categoryEl = document.getElementById("id_category");
    var valueEl = document.getElementById("id_value");
    if (!form || !valueEl) return;

    form.addEventListener("submit", function (e) {
      if (!validateAndShow(form, categoryEl, valueEl)) {
        e.preventDefault();
        valueEl.focus();
      }
    });

    valueEl.addEventListener("blur", function () {
      validateAndShow(form, categoryEl, valueEl);
    });

    if (categoryEl) {
      categoryEl.addEventListener("change", function () {
        validateAndShow(form, categoryEl, valueEl);
      });
    }
  });
})();
