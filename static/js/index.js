document.addEventListener('DOMContentLoaded', function() {
    // Keep --header-height in sync with the fixed header (its menu wraps on small
    // screens), so CSS scroll-padding-top stops anchor jumps right below it.
    const header = document.querySelector('.header');
    function headerHeight() {
        return header ? header.offsetHeight : 0;
    }
    function updateHeaderHeight() {
        document.documentElement.style.setProperty('--header-height', headerHeight() + 'px');
    }
    updateHeaderHeight();
    if (header && 'ResizeObserver' in window) {
        new ResizeObserver(updateHeaderHeight).observe(header);
    } else {
        window.addEventListener('resize', updateHeaderHeight);
    }

    function sectionFromHash(hash) {
        if (!hash || hash.length < 2) return null;
        try {
            return document.getElementById(decodeURIComponent(hash.slice(1)));
        } catch (err) {
            return null;
        }
    }

    // Smooth scrolling for in-page links, including nav links written as "/en/#news".
    document.querySelectorAll('a[href*="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const url = new URL(this.href, window.location.href);
            if (url.origin !== window.location.origin
                || url.pathname !== window.location.pathname
                || url.search !== window.location.search) {
                return; // a different page: let the browser navigate
            }
            const target = sectionFromHash(url.hash);
            if (!target) return;
            e.preventDefault();
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            if (window.location.hash !== url.hash) {
                history.pushState(null, '', url.hash);
            }
        });
    });

    // Opening a URL with a hash: the browser scrolled before --header-height was set
    // and before images loaded, so re-align once layout is final (unless the user moved).
    if (sectionFromHash(window.location.hash)) {
        let alignedAt = null;
        const align = () => {
            const target = sectionFromHash(window.location.hash);
            if (!target || (alignedAt !== null && Math.abs(window.scrollY - alignedAt) > 2)) return;
            target.scrollIntoView({ block: 'start' });
            alignedAt = window.scrollY;
        };
        requestAnimationFrame(align);
        window.addEventListener('load', align, { once: true });
    }

    // Highlight the nav item of the section currently under the header.
    function updateActiveNav() {
        let current = '';
        const offset = headerHeight() + 40;
        const sections = document.querySelectorAll('section[id]');
        sections.forEach(section => {
            if (section.getBoundingClientRect().top <= offset) {
                current = section.id;
            }
        });
        // At the very bottom the last (often short) section can never reach the header.
        const atBottom = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2;
        if (atBottom && sections.length && window.scrollY > 0) {
            current = sections[sections.length - 1].id;
        }
        document.querySelectorAll('.nav-item').forEach(item => {
            const hash = new URL(item.href, window.location.href).hash.slice(1);
            item.classList.toggle('active', !!current && hash === current);
        });
    }
    window.addEventListener('scroll', updateActiveNav, { passive: true });
    updateActiveNav();

    function fallbackCopyText(text) {
        const helper = document.createElement('textarea');
        helper.value = text;
        helper.setAttribute('readonly', 'readonly');
        helper.style.position = 'fixed';
        helper.style.top = '0';
        helper.style.left = '0';
        helper.style.opacity = '0';
        helper.style.pointerEvents = 'none';
        document.body.appendChild(helper);
        helper.focus();
        helper.select();
        helper.setSelectionRange(0, helper.value.length);
        try {
            return document.execCommand('copy');
        } catch (error) {
            return false;
        } finally {
            document.body.removeChild(helper);
        }
    }

    function resetCiteButton(button) {
        if (!button) return;
        const feedback = button.querySelector('.cite-button-feedback');
        button.classList.remove('is-copying', 'copied', 'copy-failed');
        if (feedback && feedback.dataset.copiedLabel) {
            feedback.textContent = feedback.dataset.copiedLabel;
        }
        if (button._citeResetTimer) {
            window.clearTimeout(button._citeResetTimer);
            button._citeResetTimer = null;
        }
    }

    function setCiteButtonState(button, state) {
        if (!button) return;
        const feedback = button.querySelector('.cite-button-feedback');
        resetCiteButton(button);
        if (state === 'copied') {
            if (feedback && feedback.dataset.copiedLabel) {
                feedback.textContent = feedback.dataset.copiedLabel;
            }
            button.classList.add('copied');
            button._citeResetTimer = window.setTimeout(function () {
                resetCiteButton(button);
            }, 1800);
            return;
        }
        if (state === 'failed') {
            if (feedback) {
                feedback.textContent = button.getAttribute('data-copy-error-label') || 'Copy failed';
            }
            button.classList.add('copy-failed');
            button._citeResetTimer = window.setTimeout(function () {
                resetCiteButton(button);
            }, 1800);
            return;
        }
        if (state === 'copying') {
            button.classList.add('is-copying');
        }
    }

    // Section pagination: keep per-section page state and refresh section only.
    document.addEventListener('click', function (e) {
        const citeButton = e.target.closest('.cite-button');
        if (citeButton) {
            e.preventDefault();
            const source = citeButton.parentNode ? citeButton.parentNode.querySelector('.publication-bibtex-source') : null;
            const bibtex = source ? source.value : '';
            if (!bibtex.trim()) return;

            setCiteButtonState(citeButton, 'copying');

            const handleSuccess = function () {
                setCiteButtonState(citeButton, 'copied');
            };
            const handleFailure = function () {
                setCiteButtonState(citeButton, 'failed');
            };

            if (navigator.clipboard && window.isSecureContext && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(bibtex).then(handleSuccess).catch(function () {
                    if (fallbackCopyText(bibtex)) {
                        handleSuccess();
                    } else {
                        handleFailure();
                    }
                });
            } else if (fallbackCopyText(bibtex)) {
                handleSuccess();
            } else {
                handleFailure();
            }
            return;
        }

        const link = e.target.closest('.section-pagination a.page-btn');
        if (!link) return;

        e.preventDefault();

        const currentUrl = new URL(window.location.href);
        const nextUrl = new URL(currentUrl.toString());
        const clickedUrl = new URL(link.href, window.location.origin);
        const targetSection = link.closest('section');

        if (!targetSection) return;

        clickedUrl.searchParams.forEach((value, key) => {
            nextUrl.searchParams.set(key, value);
        });
        nextUrl.hash = '#' + targetSection.id;

        targetSection.classList.add('section-loading');

        fetch(nextUrl.toString(), {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
            .then(function (response) {
                if (!response.ok) throw new Error('Request failed');
                return response.text();
            })
            .then(function (html) {
                const doc = new DOMParser().parseFromString(html, 'text/html');
                const freshSection = doc.getElementById(targetSection.id);

                if (!freshSection) throw new Error('Section not found');

                if (targetSection.parentNode) {
                    targetSection.parentNode.replaceChild(freshSection, targetSection);
                }
                window.history.replaceState({}, '', nextUrl.pathname + nextUrl.search + nextUrl.hash);
            })
            .catch(function () {
                window.location.href = nextUrl.toString();
            });
    });

    setupSectionImages();
});

/*
 * Section images: avatar-style hover (CSS) + double-click / double-tap to enlarge.
 * Card thumbnails (.news-image etc.) already have a frame; Markdown images inside
 * section content are wrapped in .zoom-frame so the hover zoom is clipped like the
 * avatar. Events are delegated, and a MutationObserver prepares images that arrive
 * with AJAX pagination.
 */
function setupSectionImages() {
    const root = document.querySelector('.main-content');
    if (!root) return;

    const isZh = (document.documentElement.lang || '').toLowerCase().indexOf('zh') === 0;
    const hint = isZh ? '双击放大' : 'Double-click to enlarge';
    const closeLabel = isZh ? '关闭' : 'Close';
    const CARD_IMAGES = '.news-image img, .publication-image img, .research-image img';
    const CONTENT_IMAGES = '.section .bio img, .section .content img, .section .description img, .section .section-content img';
    const MIN_CONTENT_SIZE = 80; // skip badges and inline icons

    // PNGs are usually transparent logos: a drop shadow around their box looks odd.
    function isPng(img) {
        try {
            return /\.png$/i.test(new URL(img.currentSrc || img.src, window.location.href).pathname);
        } catch (err) {
            return false;
        }
    }

    function prepare(img) {
        if (img.dataset.zoomable) return;
        if (img.matches(CARD_IMAGES)) {
            img.dataset.zoomable = '1';
            img.title = img.title || hint;
            if (isPng(img) && img.parentElement) img.parentElement.classList.add('zoom-frame--flat');
            return;
        }
        if (!img.matches(CONTENT_IMAGES) || img.closest('a')) return; // linked images keep their link
        const wrap = () => {
            if (img.dataset.zoomable) return;
            if (Math.max(img.naturalWidth, img.width) < MIN_CONTENT_SIZE) return;
            const frame = document.createElement('span');
            frame.className = isPng(img) ? 'zoom-frame zoom-frame--flat' : 'zoom-frame';
            img.parentNode.insertBefore(frame, img);
            frame.appendChild(img);
            img.dataset.zoomable = '1';
            img.title = img.title || hint;
        };
        if (img.complete && img.naturalWidth) wrap();
        else img.addEventListener('load', wrap, { once: true });
    }

    function prepareAll(scope) {
        scope.querySelectorAll(CARD_IMAGES + ', ' + CONTENT_IMAGES).forEach(prepare);
    }
    prepareAll(root);
    if ('MutationObserver' in window) {
        new MutationObserver(records => {
            records.forEach(record => record.addedNodes.forEach(node => {
                if (node.nodeType === 1) prepareAll(node);
            }));
        }).observe(root, { childList: true, subtree: true });
    }

    // ---- Viewer ----
    let viewer = null;
    let lastFocus = null;
    function buildViewer() {
        viewer = document.createElement('div');
        viewer.className = 'image-viewer';
        viewer.setAttribute('role', 'dialog');
        viewer.setAttribute('aria-modal', 'true');
        viewer.setAttribute('aria-hidden', 'true');
        viewer.innerHTML = '<button type="button" class="image-viewer-close"></button>'
            + '<img class="image-viewer-img" alt="">'
            + '<div class="image-viewer-caption"></div>';
        const closeBtn = viewer.querySelector('.image-viewer-close');
        closeBtn.textContent = '×';
        closeBtn.setAttribute('aria-label', closeLabel);
        closeBtn.title = closeLabel;
        viewer.addEventListener('click', event => {
            if (!event.target.classList.contains('image-viewer-img')) closeViewer();
        });
        document.body.appendChild(viewer);
    }

    function openViewer(img) {
        if (!viewer) buildViewer();
        lastFocus = document.activeElement;
        const big = viewer.querySelector('.image-viewer-img');
        big.src = img.currentSrc || img.src;
        big.alt = img.alt || '';
        viewer.querySelector('.image-viewer-caption').textContent = img.alt || '';
        viewer.setAttribute('aria-hidden', 'false');
        viewer.classList.add('is-open');
        document.body.classList.add('image-viewer-open');
        viewer.querySelector('.image-viewer-close').focus();
    }

    function closeViewer() {
        if (!viewer || !viewer.classList.contains('is-open')) return;
        viewer.classList.remove('is-open');
        viewer.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('image-viewer-open');
        if (lastFocus && typeof lastFocus.focus === 'function') lastFocus.focus();
    }

    function zoomableFrom(target) {
        const img = target && target.closest ? target.closest('img[data-zoomable]') : null;
        return img && root.contains(img) ? img : null;
    }

    root.addEventListener('dblclick', event => {
        const img = zoomableFrom(event.target);
        if (!img) return;
        event.preventDefault();
        if (window.getSelection) window.getSelection().removeAllRanges();
        openViewer(img);
    });

    // Touch screens do not reliably fire dblclick: detect a double tap ourselves.
    let lastTap = { img: null, time: 0 };
    root.addEventListener('touchend', event => {
        const img = zoomableFrom(event.target);
        if (!img || event.touches.length) return;
        const now = Date.now();
        if (lastTap.img === img && now - lastTap.time < 350) {
            event.preventDefault(); // suppresses the synthetic dblclick as well
            lastTap = { img: null, time: 0 };
            openViewer(img);
        } else {
            lastTap = { img: img, time: now };
        }
    }, { passive: false });

    document.addEventListener('keydown', event => {
        if (event.key === 'Escape') closeViewer();
    });
}
