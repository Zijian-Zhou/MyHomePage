(function () {
  function detectLanguage() {
    var path = (window.location.pathname || "").toLowerCase();
    if (path.indexOf("/zh-hans/") === 0 || path.indexOf("/zh-cn/") === 0) return "zh";
    var htmlLang = (document.documentElement.lang || "").toLowerCase();
    return htmlLang.indexOf("zh") === 0 ? "zh" : "en";
  }

  function msg(key) {
    var zh = detectLanguage() === "zh";
    var messages = {
      invalidJson: zh ? "AI \u914d\u7f6e\u5fc5\u987b\u662f\u5408\u6cd5 JSON\u3002" : "AI Configuration must be valid JSON.",
      invalidObject: zh ? "AI \u914d\u7f6e\u5fc5\u987b\u662f JSON \u5bf9\u8c61\u3002" : "AI Configuration must be a JSON object."
    };
    return messages[key];
  }

  function validateJson(value) {
    var raw = String(value || "").trim();
    if (!raw) return "";
    try {
      var payload = JSON.parse(raw);
      if (!payload || Array.isArray(payload) || typeof payload !== "object") {
        return msg("invalidObject");
      }
    } catch (e) {
      return msg("invalidJson");
    }
    return "";
  }

  function ensureErrorNode(form) {
    var list = document.getElementById("ai-config-json-messages");
    if (!list) {
      list = document.createElement("ul");
      list.id = "ai-config-json-messages";
      list.className = "messagelist";
      list.style.display = "none";
      var contentContainer = form.closest(".content") || document.querySelector(".content") || form.parentNode;
      contentContainer.insertBefore(list, form);
    }
    var item = document.getElementById("ai-config-json-error");
    if (!item) {
      item = document.createElement("li");
      item.id = "ai-config-json-error";
      item.className = "error";
      list.appendChild(item);
    }
    return item;
  }

  function validateAndShow(form, valueEl) {
    var errorNode = ensureErrorNode(form);
    var list = document.getElementById("ai-config-json-messages");
    var err = validateJson(valueEl && valueEl.value);
    if (err) {
      errorNode.textContent = err;
      if (list) list.style.display = "block";
      return false;
    }
    errorNode.textContent = "";
    if (list) list.style.display = "none";
    return true;
  }

  document.addEventListener("DOMContentLoaded", function () {
    var form = document.querySelector("form");
    var valueEl = document.getElementById("id_config_json");
    if (!form || !valueEl) return;
    form.addEventListener("submit", function (e) {
      if (!validateAndShow(form, valueEl)) {
        e.preventDefault();
        valueEl.focus();
      }
    });
    valueEl.addEventListener("blur", function () {
      validateAndShow(form, valueEl);
    });
  });
})();
