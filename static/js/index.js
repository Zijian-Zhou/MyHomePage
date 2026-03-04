document.addEventListener('DOMContentLoaded', function() {
    // Smooth scrolling for navigation links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Add active class to navigation items on scroll
    const sections = document.querySelectorAll('section');
    const navItems = document.querySelectorAll('.nav-item');

    window.addEventListener('scroll', () => {
        let current = '';
        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.clientHeight;
            if (pageYOffset >= sectionTop - 200) {
                current = section.getAttribute('id');
            }
        });

        navItems.forEach(item => {
            item.classList.remove('active');
            if (item.getAttribute('href').substring(1) === current) {
                item.classList.add('active');
            }
        });
    });

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
            const encodedBibtex = citeButton.getAttribute('data-bibtex') || '';
            const bibtex = encodedBibtex ? decodeURIComponent(encodedBibtex.replace(/\+/g, '%20')) : '';
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
});
