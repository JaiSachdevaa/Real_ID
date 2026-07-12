(function () {
    'use strict';

    const THEME_KEY = 'realid-theme';

    function getTheme() {
        return localStorage.getItem(THEME_KEY) || 'light';
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem(THEME_KEY, theme);
    }

    function toggleTheme() {
        const current = document.documentElement.getAttribute('data-theme') || 'light';
        applyTheme(current === 'dark' ? 'light' : 'dark');
    }

    // Apply theme immediately to avoid a flash of the wrong theme
    applyTheme(getTheme());

    document.addEventListener('DOMContentLoaded', () => {
        const themeBtn = document.getElementById('themeToggle');
        if (themeBtn) themeBtn.addEventListener('click', toggleTheme);

        const menuToggle = document.getElementById('menuToggle');
        const mobileMenu = document.getElementById('mobileMenu');
        if (menuToggle && mobileMenu) {
            menuToggle.addEventListener('click', () => {
                const isOpen = mobileMenu.classList.toggle('open');
                menuToggle.classList.toggle('active', isOpen);
                document.body.style.overflow = isOpen ? 'hidden' : '';
            });
        }

        document.querySelectorAll('a[href^="#"]').forEach(link => {
            link.addEventListener('click', (e) => {
                const target = document.querySelector(link.getAttribute('href'));
                if (target) {
                    e.preventDefault();
                    closeMobileMenu();
                    const offset = 72;
                    const top = target.getBoundingClientRect().top + window.scrollY - offset;
                    window.scrollTo({ top, behavior: 'smooth' });
                }
            });
        });
    });

    window.closeMobileMenu = function () {
        const mobileMenu = document.getElementById('mobileMenu');
        const menuToggle = document.getElementById('menuToggle');
        if (mobileMenu) mobileMenu.classList.remove('open');
        if (menuToggle) menuToggle.classList.remove('active');
        document.body.style.overflow = '';
    };

    window.showAlert = function (id, msg, type = 'error') {
        const el = document.getElementById(id);
        if (!el) return;
        const icon = type === 'success'
            ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>'
            : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>';
        el.className = `alert alert-${type} show`;
        el.innerHTML = `${icon}<span>${msg}</span>`;
        if (type === 'success') {
            setTimeout(() => el.classList.remove('show'), 4000);
        }
    };

    window.hideAlert = function (id) {
        const el = document.getElementById(id);
        if (el) el.classList.remove('show');
    };

    window.setButtonLoading = function (btn, loading, label = '') {
        if (loading) {
            btn.disabled = true;
            btn.dataset.originalText = btn.innerHTML;
            btn.innerHTML = `<span class="spinner"></span> ${label || 'Loading...'}`;
        } else {
            btn.disabled = false;
            btn.innerHTML = btn.dataset.originalText || label;
        }
    };
})();