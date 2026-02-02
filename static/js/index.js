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

    // Mobile menu toggle
    const navbar = document.querySelector('.navbar');
    const navbarMenu = document.querySelector('.navbar-menu');
    
    // Add mobile menu button if not exists
    if (!document.querySelector('.mobile-menu-btn')) {
        const mobileMenuBtn = document.createElement('button');
        mobileMenuBtn.className = 'mobile-menu-btn';
        mobileMenuBtn.innerHTML = '<i class="fas fa-bars"></i>';
        navbar.insertBefore(mobileMenuBtn, navbarMenu);

        mobileMenuBtn.addEventListener('click', () => {
            navbarMenu.classList.toggle('active');
        });
    }

    // Section pagination: keep per-section page state and refresh section only.
    document.addEventListener('click', function (e) {
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
