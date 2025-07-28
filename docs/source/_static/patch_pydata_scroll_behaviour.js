// from https://github.com/pydata/pydata-sphinx-theme/issues/1889#issuecomment-2523346100
document.addEventListener('DOMContentLoaded', function () {
    const sections = document.querySelectorAll('section'); // All content sections
    const tocLinks = document.querySelectorAll('.bd-toc li a'); // All TOC links
    let uncollapseTimeout; // Timeout variable for debouncing
    const offset = window.innerHeight * 0.12; // Offset for activating sections, 12% of the viewport height

    /* Add a debug line for visualization at the offset position */
    // const debugLine = document.createElement('div');
    // debugLine.style.position = 'fixed';
    // debugLine.style.top = `${offset}px`;
    // debugLine.style.left = '0';
    // debugLine.style.width = '100%';
    // debugLine.style.height = '2px';
    // debugLine.style.backgroundColor = 'red';
    // debugLine.style.zIndex = '9999';
    // document.body.appendChild(debugLine);

    /**
     * Scroll event handler to determine the active section and update the TOC.
     */
    window.addEventListener('scroll', function () {
        const scrollPosition = window.scrollY + offset; // Adjusted scroll position with offset
        let activeSection = null;

        // Determine which section is currently visible
        sections.forEach(section => {
            const rect = section.getBoundingClientRect();
            const sectionTop = rect.top + window.scrollY; // Absolute position of the section
            const sectionBottom = sectionTop + section.offsetHeight;

            if (scrollPosition >= sectionTop && scrollPosition <= sectionBottom) {
                activeSection = section;
            }
        });

        // Update TOC if there's an active section
        if (activeSection) {
            activateTocForSection(activeSection);
        }
    });

    /**
     * Activate the TOC link corresponding to a given section.
     * @param {HTMLElement} section - The currently active section.
     */
    function activateTocForSection(section) {
        const id = section.id;
        if (!id) return;

        // Remove 'active' class from all TOC links
        tocLinks.forEach(link => link.classList.remove('active'));

        // Add 'active' class to the corresponding TOC link
        const tocLink = document.querySelector(`.bd-toc li a[href="#${id}"]`);
        if (tocLink) {
            tocLink.classList.add('active');
            highlightParents(tocLink); // Highlight all parent TOC links
            uncollapseParents(tocLink); // Uncollapse parent levels
        }
    }

    /**
     * Highlight all parent TOC links of the current link.
     * @param {HTMLElement} link - The currently active TOC link.
     */
    function highlightParents(link) {
        let currentItem = link.closest('li');

        // Traverse up the TOC hierarchy and add 'active' class to parents
        while (currentItem) {
            const parentNavLink = currentItem.parentElement.closest('li')?.querySelector('a');
            if (parentNavLink) {
                parentNavLink.classList.add('active');
                currentItem = parentNavLink.closest('li');
            } else {
                currentItem = null; // Stop if no more parents
            }
        }
    }

    /**
     * Initialize TOC state on page load.
     * If a hash is present in the URL, scroll to and activate the corresponding section.
     */
    const hash = window.location.hash;
    if (hash) {
        const targetElement = document.querySelector(hash);
        if (targetElement) {
            activateTocForSection(targetElement);
            targetElement.scrollIntoView({ behavior: 'smooth' });
        }
    }
});
