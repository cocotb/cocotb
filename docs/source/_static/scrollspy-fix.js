// Fix for Bootstrap Scrollspy (pydata-sphinx-theme#1889)
// The IDs are on SECTIONS not on HEADINGS
(function() {
    'use strict';

    function getElementOffset(el) {
        let top = 0;
        while (el) {
            top += el.offsetTop;
            el = el.offsetParent;
        }
        return top;
    }

    function fixScrollspy() {
        console.log('Scrollspy Fix is initializing...');

        const header = document.querySelector('.bd-header');
        if (!header) {
            console.error('Header not found');
            return;
        }

        const headerHeight = header.offsetHeight;
        const offset = headerHeight + 100;

        console.log('Offset:', offset + 'px (Header: ' + headerHeight + 'px)');

        const tocLinks = document.querySelectorAll('.bd-toc-nav a.nav-link');
        if (tocLinks.length === 0) {
            console.error('No TOC links found');
            return;
        }

        console.log('TOC links found:', tocLinks.length);

        // Click handler for each TOC link
        tocLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                const href = this.getAttribute('href');
                if (!href || href === '#') return;

                e.preventDefault();

                const targetElement = document.querySelector(href);
                if (targetElement) {
                    const elementTop = getElementOffset(targetElement);
                    const targetPosition = elementTop - offset;

                    console.log('Scrolling to ' + href + ' - Position: ' + targetPosition + 'px');

                    window.scrollTo({
                        top: targetPosition,
                        behavior: 'smooth'
                    });

                    // Collect all parent links of the clicked link
                    const clickedLi = this.closest('li');
                    const parentLinks = [];

                    let currentLi = clickedLi;
                    while (currentLi) {
                        const parentUl = currentLi.parentElement;
                        if (!parentUl) break;

                        const parentLi = parentUl.closest('li');
                        if (!parentLi) break;

                        const parentLink = parentLi.querySelector(':scope > a.nav-link');
                        if (parentLink) {
                            parentLinks.push(parentLink);
                        }

                        currentLi = parentLi;
                    }

                    // Remove active from all links except the clicked one and its parents
                    tocLinks.forEach(l => {
                        if (l !== this && !parentLinks.includes(l)) {
                            l.classList.remove('active');
                        }
                    });

                    // Activate the clicked link
                    this.classList.add('active');

                    // Also activate all parent links
                    parentLinks.forEach(pl => pl.classList.add('active'));

                    console.log('Activated: ' + href);
                }
            });
        });

        // Scroll handler
        let ticking = false;

        function updateActiveLink() {
            const scrollTop = window.pageYOffset;

            // Find all sections with IDs (not headings!)
            const sections = Array.from(document.querySelectorAll('section[id]'));

            let activeId = null;

            // Find the active section
            for (let i = sections.length - 1; i >= 0; i--) {
                const section = sections[i];
                const sectionTop = getElementOffset(section);

                if (scrollTop + offset >= sectionTop - 50) {
                    activeId = section.id;
                    break;
                }
            }

            // Remove all active classes
            tocLinks.forEach(link => link.classList.remove('active'));

            // Set new active class
            if (activeId) {
                const activeLink = document.querySelector('.bd-toc-nav a.nav-link[href="#' + activeId + '"]');
                if (activeLink) {
                    activeLink.classList.add('active');

                    // Activate parent links
                    let parentLi = activeLink.closest('li');
                    while (parentLi) {
                        const parentLink = parentLi.querySelector(':scope > a.nav-link');
                        if (parentLink && parentLink !== activeLink) {
                            parentLink.classList.add('active');
                        }
                        const nextParent = parentLi.parentElement;
                        parentLi = nextParent ? nextParent.closest('li') : null;
                    }
                }
            }

            ticking = false;
        }

        window.addEventListener('scroll', function() {
            if (!ticking) {
                window.requestAnimationFrame(updateActiveLink);
                ticking = true;
            }
        }, { passive: true });

        // Initial update
        setTimeout(updateActiveLink, 500);

        console.log('Scrollspy Fix activated!');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fixScrollspy);
    } else {
        fixScrollspy();
    }
})();
