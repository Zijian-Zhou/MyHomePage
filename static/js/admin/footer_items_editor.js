/*
 * Row-based editor for the "footer_items" System Configuration entry.
 * The original JSON textarea stays in the form (hidden) and is kept in sync, so the
 * server receives {"item": [{"content": ..., "icon": ..., "href": ...}, ...]}.
 */
(function () {
  var ICON_CLASS_RE = /^[a-z][a-z0-9-]*(?: [a-z][a-z0-9-]*){0,5}$/;

  function readJsonScript(id) {
    var el = document.getElementById(id);
    if (!el) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      return null;
    }
  }

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (key) {
      if (key === "text") node.textContent = attrs[key];
      else if (key === "className") node.className = attrs[key];
      else node.setAttribute(key, attrs[key]);
    });
    (children || []).forEach(function (child) {
      node.appendChild(child);
    });
    return node;
  }

  function parseItems(raw) {
    raw = String(raw || "").trim();
    if (!raw) return [];
    var payload = JSON.parse(raw); // throws on invalid JSON
    var data = payload && payload.item;
    if (data && !Array.isArray(data) && typeof data === "object") data = [data];
    if (!Array.isArray(data)) throw new Error("invalid item");
    return data.map(function (entry) {
      entry = entry || {};
      return {
        content: String(entry.content || ""),
        icon: String(entry.icon || ""),
        href: String(entry.href || "")
      };
    });
  }

  function iconPreview(icon) {
    icon = String(icon || "").trim();
    if (!icon) return null;
    if (ICON_CLASS_RE.test(icon)) {
      return el("i", { className: icon, "aria-hidden": "true" });
    }
    if (/^(https?:\/\/|\/(?!\/))/i.test(icon)) {
      return el("img", { src: icon, alt: "", className: "footer-editor-icon-img" });
    }
    return el("span", { className: "footer-editor-icon-invalid", text: "?" });
  }

  function init() {
    var valueEl = document.getElementById("id_value");
    var categoryEl = document.getElementById("id_category");
    var current = readJsonScript("systemconfig-current-category") || (categoryEl && categoryEl.value) || "";
    if (!valueEl || current !== "footer_items") return;

    var labels = readJsonScript("footer-editor-labels") || {};
    var form = valueEl.form;
    var items;
    var rawMode = false;
    try {
      items = parseItems(valueEl.value);
    } catch (e) {
      items = [];
      rawMode = true; // keep invalid legacy JSON visible so nothing is silently lost
    }

    var tbody = el("tbody");
    var table = el("table", { className: "footer-editor-table" }, [
      el("thead", {}, [el("tr", {}, [
        el("th", { text: labels.name || "Name" }),
        el("th", { text: labels.icon || "Icon" }),
        el("th", { className: "footer-editor-preview-col", text: labels.preview || "Preview" }),
        el("th", { text: labels.link || "Link" }),
        el("th", { className: "footer-editor-actions-col", text: labels.actions || "Actions" })
      ])]),
      tbody
    ]);
    var emptyNote = el("p", { className: "footer-editor-empty", text: labels.empty || "" });
    var errorNote = el("p", { className: "footer-editor-error", role: "alert" });
    var addBtn = el("button", { type: "button", className: "button footer-editor-add", text: "+ " + (labels.add || "Add") });
    var rawToggle = el("button", { type: "button", className: "button footer-editor-raw-toggle", text: labels.raw_toggle || "Edit raw JSON" });
    var editor = el("div", { className: "footer-editor" }, [
      el("p", { className: "footer-editor-hint", text: labels.hint || "" }),
      el("div", { className: "footer-editor-scroll" }, [table]),
      emptyNote,
      errorNote,
      el("div", { className: "footer-editor-toolbar" }, [addBtn, rawToggle])
    ]);
    valueEl.parentNode.insertBefore(editor, valueEl);

    function sync() {
      var out = [];
      items.forEach(function (item) {
        var content = item.content.trim();
        var icon = item.icon.trim();
        var href = item.href.trim();
        if (!content && !icon && !href) return; // ignore fully blank rows
        var entry = { content: content };
        if (icon) entry.icon = icon;
        if (href) entry.href = href;
        out.push(entry);
      });
      valueEl.value = out.length ? JSON.stringify({ item: out }) : "";
    }

    function hasMissingName() {
      return items.some(function (item) {
        return !item.content.trim() && (item.icon.trim() || item.href.trim());
      });
    }

    function actionButton(text, title, handler, disabled) {
      var btn = el("button", { type: "button", className: "footer-editor-btn", title: title, "aria-label": title, text: text });
      if (disabled) btn.disabled = true;
      btn.addEventListener("click", handler);
      return btn;
    }

    function render() {
      tbody.innerHTML = "";
      items.forEach(function (item, index) {
        var nameInput = el("input", { type: "text", value: item.content, placeholder: labels.name_placeholder || "", maxlength: "200" });
        var iconInput = el("input", { type: "text", value: item.icon, placeholder: labels.icon_placeholder || "", maxlength: "500" });
        var linkInput = el("input", { type: "text", value: item.href, placeholder: labels.link_placeholder || "", maxlength: "1000" });
        var previewCell = el("td", { className: "footer-editor-preview" });

        function refreshPreview() {
          previewCell.innerHTML = "";
          var preview = iconPreview(item.icon);
          if (preview) previewCell.appendChild(preview);
        }

        nameInput.addEventListener("input", function () {
          item.content = nameInput.value;
          nameInput.classList.toggle("footer-editor-invalid", false);
          errorNote.textContent = "";
          sync();
        });
        iconInput.addEventListener("input", function () {
          item.icon = iconInput.value;
          refreshPreview();
          sync();
        });
        linkInput.addEventListener("input", function () {
          item.href = linkInput.value;
          sync();
        });
        refreshPreview();

        tbody.appendChild(el("tr", {}, [
          el("td", {}, [nameInput]),
          el("td", {}, [iconInput]),
          previewCell,
          el("td", {}, [linkInput]),
          el("td", { className: "footer-editor-actions" }, [
            actionButton("↑", labels.up || "Up", function () {
              items.splice(index - 1, 0, items.splice(index, 1)[0]);
              render();
            }, index === 0),
            actionButton("↓", labels.down || "Down", function () {
              items.splice(index + 1, 0, items.splice(index, 1)[0]);
              render();
            }, index === items.length - 1),
            actionButton("×", labels.remove || "Remove", function () {
              items.splice(index, 1);
              render();
            })
          ])
        ]));
      });
      emptyNote.style.display = items.length ? "none" : "";
      table.style.display = items.length ? "" : "none";
      sync();
    }

    function setRawMode(enabled) {
      if (!enabled) {
        try {
          items = parseItems(valueEl.value);
        } catch (e) {
          errorNote.textContent = labels.invalid_json || "Invalid JSON.";
          return;
        }
        errorNote.textContent = "";
        render();
      }
      rawMode = enabled;
      valueEl.style.display = enabled ? "" : "none";
      editor.classList.toggle("footer-editor-raw", enabled);
    }

    addBtn.addEventListener("click", function () {
      items.push({ content: "", icon: "", href: "" });
      render();
      var inputs = tbody.querySelectorAll("tr:last-child input");
      if (inputs.length) inputs[0].focus();
    });
    rawToggle.addEventListener("click", function () {
      setRawMode(!rawMode);
    });

    if (form) {
      form.addEventListener("submit", function (event) {
        if (rawMode) return; // the JSON validator and the server check raw input
        if (hasMissingName()) {
          event.preventDefault();
          event.stopImmediatePropagation();
          errorNote.textContent = labels.name_required || "Display name is required.";
          tbody.querySelectorAll("tr").forEach(function (row, index) {
            var item = items[index];
            var input = row.querySelector("input");
            var missing = item && !item.content.trim() && (item.icon.trim() || item.href.trim());
            if (input) input.classList.toggle("footer-editor-invalid", !!missing);
          });
          return;
        }
        sync();
      }, true);
    }

    if (rawMode) {
      valueEl.style.display = "";
      editor.classList.add("footer-editor-raw");
    } else {
      valueEl.style.display = "none";
      render();
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
