(function () {
    'use strict';

    const THEME_KEY = 'realid-theme';

    function getTheme() {
        return localStorage.getItem(THEME_KEY) ||
            (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        const icon = document.querySelector('.theme-icon');
        if (icon) icon.textContent = theme === 'dark' ? '☀️' : '🌙';
        localStorage.setItem(THEME_KEY, theme);
    }

    function toggleTheme() {
        const current = document.documentElement.getAttribute('data-theme') || 'dark';
        const next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.style.transition = 'background 0.4s, color 0.4s';
        applyTheme(next);
        const btn = document.getElementById('themeToggle');
        if (btn) {
            btn.style.transform = 'scale(0.85) rotate(180deg)';
            setTimeout(() => { btn.style.transform = ''; }, 300);
        }
    }

    // Init theme immediately to avoid flash
    applyTheme(getTheme());

    document.addEventListener('DOMContentLoaded', () => {
        const themeBtn = document.getElementById('themeToggle');
        if (themeBtn) themeBtn.addEventListener('click', toggleTheme);

        const nav = document.getElementById('main-nav');
        if (nav) {
            window.addEventListener('scroll', () => {
                nav.classList.toggle('scrolled', window.scrollY > 20);
            }, { passive: true });
        }

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
                    const offset = 80;
                    const top = target.getBoundingClientRect().top + window.scrollY - offset;
                    window.scrollTo({ top, behavior: 'smooth' });
                }
            });
        });

        let cursorGlow = document.querySelector('.cursor-glow');
        if (!cursorGlow) {
            cursorGlow = document.createElement('div');
            cursorGlow.className = 'cursor-glow';
            cursorGlow.style.cssText = `
                position: fixed;
                width: 320px; height: 320px;
                pointer-events: none;
                background: radial-gradient(circle, rgba(79,140,255,0.045) 0%, transparent 70%);
                border-radius: 50%;
                transform: translate(-50%,-50%);
                z-index: 0;
                transition: opacity 0.3s;
                opacity: 0;
            `;
            document.body.appendChild(cursorGlow);
        }

        document.addEventListener('mousemove', (e) => {
            cursorGlow.style.left = e.clientX + 'px';
            cursorGlow.style.top  = e.clientY + 'px';
            cursorGlow.style.opacity = '1';
        });

        document.addEventListener('mouseleave', () => { cursorGlow.style.opacity = '0'; });

        document.body.classList.add('page-enter');

        if (typeof gsap === 'undefined') {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.style.opacity = '1';
                        entry.target.style.transform = 'translateY(0)';
                        observer.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.1 });

            document.querySelectorAll('.feature-card, .step, .stat-item').forEach(el => {
                el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
                observer.observe(el);
            });
        }
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
        el.className = `alert alert-${type} show`;
        el.textContent = msg;
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