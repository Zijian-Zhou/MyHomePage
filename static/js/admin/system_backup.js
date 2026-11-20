(function () {
  var labelsEl = document.getElementById("system-backup-labels");
  var labels = {};
  try {
    labels = JSON.parse((labelsEl && labelsEl.textContent) || "{}");
  } catch (e) {
    labels = {};
  }
  var overlay = document.querySelector("[data-backup-overlay]");

  function showBusy() {
    if (overlay) overlay.hidden = false;
    document.querySelectorAll(".system-backup button[type=submit]").forEach(function (btn) {
      btn.disabled = true;
    });
  }

  function formatSize(bytes) {
    var units = ["B", "KB", "MB", "GB"];
    var value = bytes;
    var unit = 0;
    while (value >= 1024 && unit < units.length - 1) {
      value /= 1024;
      unit += 1;
    }
    return (unit === 0 ? value : value.toFixed(1)) + " " + units[unit];
  }

  function setupImportDropzone(form) {
    var zone = form.querySelector("[data-backup-dropzone]");
    var input = form.querySelector("[data-backup-file]");
    var title = form.querySelector("[data-backup-drop-title]");
    var chip = form.querySelector("[data-backup-file-info]");
    var nameEl = form.querySelector("[data-backup-file-name]");
    var sizeEl = form.querySelector("[data-backup-file-size]");
    var removeBtn = form.querySelector("[data-backup-file-remove]");
    var errorEl = form.querySelector("[data-backup-file-error]");
    var submitBtn = form.querySelector("[data-backup-import-submit]");
    if (!zone || !input) return;
    var defaultTitle = title ? title.textContent : "";
    var dragDepth = 0;

    function isZip(file) {
      return !!file && /\.zip$/i.test(file.name || "");
    }

    function showError(message) {
      zone.classList.toggle("is-invalid", !!message);
      if (!errorEl) return;
      errorEl.textContent = message || "";
      errorEl.hidden = !message;
    }

    function refresh() {
      var file = input.files && input.files[0];
      var valid = isZip(file);
      if (file && !valid) {
        input.value = "";
        showError(labels.invalid_type || "Please choose a .zip file.");
      } else {
        showError("");
      }
      if (chip) chip.hidden = !valid;
      if (valid) {
        if (nameEl) nameEl.textContent = file.name;
        if (sizeEl) sizeEl.textContent = formatSize(file.size);
      }
      if (submitBtn) submitBtn.disabled = !valid;
    }

    input.addEventListener("change", refresh);

    if (removeBtn) {
      removeBtn.addEventListener("click", function () {
        input.value = "";
        refresh();
        input.focus();
      });
    }

    ["dragenter", "dragover"].forEach(function (type) {
      zone.addEventListener(type, function (event) {
        event.preventDefault();
        if (type === "dragenter") dragDepth += 1;
        if (event.dataTransfer) event.dataTransfer.dropEffect = "copy";
        zone.classList.add("is-dragover");
        if (title) title.textContent = labels.drop_active || defaultTitle;
      });
    });

    function endDrag() {
      dragDepth = 0;
      zone.classList.remove("is-dragover");
      if (title) title.textContent = defaultTitle;
    }

    zone.addEventListener("dragleave", function () {
      dragDepth -= 1;
      if (dragDepth <= 0) endDrag();
    });

    zone.addEventListener("drop", function (event) {
      event.preventDefault();
      endDrag();
      var files = event.dataTransfer && event.dataTransfer.files;
      if (!files || !files.length) return;
      if (!isZip(files[0])) {
        input.value = "";
        refresh();
        showError(labels.invalid_type || "Please choose a .zip file.");
        return;
      }
      try {
        var transfer = new DataTransfer();
        transfer.items.add(files[0]);
        input.files = transfer.files;
      } catch (e) {
        input.files = files;
      }
      refresh();
    });

    // Dropping a file outside the zone would otherwise make the browser open it.
    window.addEventListener("dragover", function (event) { event.preventDefault(); });
    window.addEventListener("drop", function (event) { event.preventDefault(); });

    form.addEventListener("submit", function (event) {
      if (!isZip(input.files && input.files[0])) {
        event.preventDefault();
        event.stopImmediatePropagation();
        showError(labels.invalid_type || "Please choose a .zip file.");
      }
    }, true);

    refresh();
  }

  document.querySelectorAll("[data-backup-import]").forEach(setupImportDropzone);

  document.querySelectorAll(".system-backup form").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      var kind = form.getAttribute("data-backup-confirm");
      if (kind) {
        var template = labels["confirm_" + kind] || "";
        var message = template.replace("{name}", form.getAttribute("data-backup-name") || "");
        if (message && !window.confirm(message)) {
          event.preventDefault();
          return;
        }
      }
      if (form.hasAttribute("data-backup-busy")) {
        // Disable after the browser has captured the submitted form data.
        window.setTimeout(showBusy, 0);
      }
    });
  });
})();
