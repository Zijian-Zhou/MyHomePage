(function () {
  function basename(path) {
    var file = (path || '').split(/[\\/]/).pop();
    return file.replace(/\.[^.]+$/, '');
  }

  document.addEventListener('DOMContentLoaded', function () {
    var fileInput = document.getElementById('id_file');
    var titleInput = document.getElementById('id_title');
    if (!fileInput || !titleInput) return;

    fileInput.addEventListener('change', function () {
      if ((titleInput.value || '').trim()) return;
      var name = basename(fileInput.value);
      if (name) titleInput.value = name;
    });
  });
})();
