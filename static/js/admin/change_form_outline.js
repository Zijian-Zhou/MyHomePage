(function () {
  function textOf(node) {
    return (node && node.textContent ? node.textContent : '').replace(/\s+/g, ' ').trim();
  }

  function isChangeFormPage() {
    return !!document.querySelector('#content-main form');
  }

  function directHeadingText(node) {
    const children = Array.prototype.slice.call(node.children || []);
    for (let i = 0; i < children.length; i += 1) {
      const child = children[i];
      if (child && /^(H2|H3)$/i.test(child.tagName || '')) return textOf(child);
    }
    return '';
  }

  function zhTitle(title) {
    const map = {
      'Basic Information': '\u57fa\u672c\u4fe1\u606f',
      'Detail Page': '\u8be6\u60c5\u9875',
      'Author Settings': '\u4f5c\u8005\u8bbe\u7f6e',
      'Links': '\u94fe\u63a5',
      'BibTeX Information': 'BibTeX \u4fe1\u606f',
      'BibTeX Import': 'BibTeX \u5bfc\u5165',
      'File List': '\u6587\u4ef6\u5217\u8868',
      'Media': '\u5a92\u4f53',
      'Timestamps': '\u65f6\u95f4\u6233',
      'Availability Check': '\u53ef\u7528\u6027\u68c0\u6d4b',
      'Advanced Configuration': '\u9ad8\u7ea7\u914d\u7f6e'
    };
    return map[title] || title;
  }

  function collectSections(isZh) {
    const rawNodes = Array.prototype.slice.call(document.querySelectorAll(
      '#content-main form > div > fieldset.module, #content-main form > fieldset.module, #content-main .inline-group'
    ));
    const seen = {};
    return rawNodes.map(function (node, index) {
      if (node.tagName === 'FIELDSET' && node.closest('.inline-group')) return null;
      let title = '';
      if (node.classList.contains('inline-group')) {
        title = textOf(node.querySelector('.inline-related > fieldset.module > h2'));
      }
      if (!title) title = directHeadingText(node);
      if (!title) title = isZh ? '\u5355\u5143 ' + (index + 1) : 'Section ' + (index + 1);
      if (isZh) title = zhTitle(title);
      if (!node.id) node.id = 'admin-outline-section-' + index;
      const key = node.id + '|' + title;
      if (seen[key]) return null;
      seen[key] = true;
      return { id: node.id, title: title };
    }).filter(function (item) {
      return item.title;
    });
  }

  function buildOutline(sections) {
    const isZh = /^\/zh/i.test(window.location.pathname || '');
    const panel = document.createElement('aside');
    panel.className = 'admin-detail-outline';
    panel.innerHTML = [
      '<button type="button" class="admin-outline-toggle" aria-expanded="true">',
      isZh ? '&#25910;&#36215;&#22823;&#32434;' : 'Collapse outline',
      '</button>',
      '<div class="admin-outline-body">',
      '<div class="admin-outline-title">' + (isZh ? '&#39029;&#38754;&#22823;&#32434;' : 'Outline') + '</div>',
      '<nav class="admin-outline-nav"></nav>',
      '</div>'
    ].join('');

    const nav = panel.querySelector('.admin-outline-nav');
    sections.forEach(function (section) {
      const link = document.createElement('a');
      link.href = '#' + section.id;
      link.textContent = section.title;
      link.addEventListener('click', function (event) {
        event.preventDefault();
        const target = document.getElementById(section.id);
        if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
      nav.appendChild(link);
    });

    const toggle = panel.querySelector('.admin-outline-toggle');
    toggle.addEventListener('click', function () {
      const collapsed = panel.classList.toggle('is-collapsed');
      toggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
      toggle.innerHTML = collapsed
        ? (isZh ? '&#23637;&#24320;&#22823;&#32434;' : 'Expand outline')
        : (isZh ? '&#25910;&#36215;&#22823;&#32434;' : 'Collapse outline');
    });
    return panel;
  }

  document.addEventListener('DOMContentLoaded', function () {
    if (!isChangeFormPage() || document.querySelector('.admin-detail-outline')) return;
    const isZh = /^\/zh/i.test(window.location.pathname || '');
    const sections = collectSections(isZh);
    if (!sections.length) return;
    document.body.classList.add('has-admin-detail-outline');
    document.body.appendChild(buildOutline(sections));
  });
})();
