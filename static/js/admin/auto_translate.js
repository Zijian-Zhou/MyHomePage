(function () {
  function getCookie(name) {
    var value = "; " + document.cookie;
    var parts = value.split("; " + name + "=");
    if (parts.length === 2) return decodeURIComponent(parts.pop().split(";").shift());
    return "";
  }

  function isZhPage() {
    var path = (window.location.pathname || "").toLowerCase();
    return path.indexOf("/zh-hans/") === 0 || path.indexOf("/zh-cn/") === 0;
  }

  var messages = {
    en: {
      translateZh: "Translate Chinese",
      translateEn: "Translate English",
      noText: "No text",
      translating: "Translating...",
      done: "Done",
      failed: "Failed"
    },
    zh: {
      translateZh: "\u7ffb\u8bd1\u4e2d\u6587",
      translateEn: "\u7ffb\u8bd1\u82f1\u6587",
      noText: "\u65e0\u53ef\u7ffb\u8bd1\u5185\u5bb9",
      translating: "\u6b63\u5728\u7ffb\u8bd1...",
      done: "\u5df2\u5b8c\u6210",
      failed: "\u7ffb\u8bd1\u5931\u8d25"
    }
  };

  function msg(key) {
    return messages[isZhPage() ? "zh" : "en"][key];
  }

  function getCsrfToken() {
    var fieldToken = document.querySelector("input[name='csrfmiddlewaretoken']");
    if (fieldToken && fieldToken.value) return fieldToken.value;
    return getCookie("csrftoken");
  }

  function isEditableField(el) {
    if (!el || el.disabled || el.readOnly) return false;
    if (el.tagName !== "TEXTAREA" && el.tagName !== "INPUT") return false;
    var type = (el.getAttribute("type") || "text").toLowerCase();
    return ["text", "url", "email", "search", "tel"].indexOf(type) !== -1 || el.tagName === "TEXTAREA";
  }

  function setStatus(button, text, isError) {
    button.textContent = text;
    button.classList.toggle("auto-translate-error", !!isError);
  }

  function dispatchInput(el) {
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function languageOfField(el) {
    return /_zh$/.test(el.name || el.id || "") ? "zh" : "en";
  }

  function labelForTarget(targetLang) {
    return targetLang === "zh" ? msg("translateZh") : msg("translateEn");
  }

  function insertAfterField(field, button) {
    var wrapper = document.createElement("div");
    wrapper.className = "auto-translate-control";
    wrapper.appendChild(button);

    if (field.parentNode) {
      field.parentNode.insertBefore(wrapper, field.nextSibling);
    }
  }

  async function translateText(text, sourceLang, targetLang) {
    var csrfToken = getCsrfToken();
    var headers = {
      "Content-Type": "application/json"
    };
    if (csrfToken) {
      headers["X-CSRFToken"] = csrfToken;
    }

    var response = await fetch(window.HOMEPAGE_ADMIN_TRANSLATE_URL, {
      method: "POST",
      credentials: "same-origin",
      headers: headers,
      body: JSON.stringify({
        text: text,
        source_lang: sourceLang,
        target_lang: targetLang
      })
    });

    var data = await response.json().catch(function () { return {}; });
    if (!response.ok) {
      throw new Error(data.error || msg("failed"));
    }
    return data.translated_text || "";
  }

  function addButton(sourceField, targetField) {
    if (!isEditableField(sourceField) || !isEditableField(targetField)) return;
    if (sourceField.dataset.autoTranslateReady === "1") return;
    sourceField.dataset.autoTranslateReady = "1";

    var sourceLang = languageOfField(sourceField);
    var targetLang = languageOfField(targetField);
    var button = document.createElement("button");
    button.type = "button";
    button.className = "button auto-translate-button";
    button.textContent = labelForTarget(targetLang);

    button.addEventListener("click", async function () {
      var fromField = sourceField;
      var toField = targetField;
      var fromLang = sourceLang;
      var toLang = targetLang;

      if (!String(fromField.value || "").trim() && String(toField.value || "").trim()) {
        fromField = targetField;
        toField = sourceField;
        fromLang = targetLang;
        toLang = sourceLang;
      }

      var sourceText = String(fromField.value || "").trim();
      if (!sourceText) {
        setStatus(button, msg("noText"), true);
        window.setTimeout(function () { setStatus(button, labelForTarget(targetLang), false); }, 1400);
        return;
      }

      var originalLabel = button.textContent;
      button.disabled = true;
      setStatus(button, msg("translating"), false);

      try {
        var translated = await translateText(sourceText, fromLang, toLang);
        toField.value = translated;
        dispatchInput(toField);
        setStatus(button, msg("done"), false);
      } catch (error) {
        setStatus(button, error.message || msg("failed"), true);
      } finally {
        window.setTimeout(function () {
          button.disabled = false;
          setStatus(button, originalLabel, false);
        }, 1600);
      }
    });

    insertAfterField(sourceField, button);
  }

  function wirePairs(root) {
    root = root || document;
    var zhFields = root.querySelectorAll("input[id$='_zh'], textarea[id$='_zh']");
    zhFields.forEach(function (zhField) {
      var baseId = zhField.id.replace(/_zh$/, "");
      var baseField = document.getElementById(baseId);
      if (!baseField) return;
      addButton(baseField, zhField);
      addButton(zhField, baseField);
    });
  }

  function injectStyle() {
    if (document.getElementById("auto-translate-style")) return;
    var style = document.createElement("style");
    style.id = "auto-translate-style";
    style.textContent = [
      ".auto-translate-control{margin:18px 0 12px;}",
      ".flex-container>.auto-translate-control{margin:0 0 0 18px;}",
      ".auto-translate-button{font-size:12px;line-height:1.4;padding:4px 10px;}",
      ".auto-translate-button.auto-translate-error{border-color:#ba2121;color:#ba2121;}",
      "html[data-theme='dark'] .auto-translate-button.auto-translate-error,body.dark-mode .auto-translate-button.auto-translate-error{border-color:#ff8a8a;color:#ffb1b1;}"
    ].join("");
    document.head.appendChild(style);
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!window.HOMEPAGE_ADMIN_TRANSLATE_URL) return;
    injectStyle();
    wirePairs(document);

    var observer = new MutationObserver(function (mutations) {
      mutations.forEach(function (mutation) {
        mutation.addedNodes.forEach(function (node) {
          if (node.nodeType === 1) wirePairs(node);
        });
      });
    });
    observer.observe(document.body, { childList: true, subtree: true });
  });
})();
