/**
 * Enhanced TOC syncing using sphinx-nefertiti's multi-threshold approach
 * Adapted for sphinx-book-theme/pydata-sphinx-theme structure
 *
 * This script REPLACES pydata's default TOC syncing with nefertiti's implementation
 */
(function() {
  'use strict';

  // Module-level flag
  let cocotbObserverActive = false;  // Whether our observer is initialized

  class TocObserver {
    constructor() {
      this.toc = null;
      this.observer = null;
      this.disableObserver = false;
    }

    /**
     * Handler for IntersectionObserver
     * Exact sphinx-nefertiti logic: add/remove active on parent element
     * Also add to link itself to match PST's selector
     */
    _handleIntersection = (entries) => {
      if (this.disableObserver) return;

      // Only process if our observer is active (ignore pydata's observer)
      if (!cocotbObserverActive) return;

      const toc = this.toc; // Capture in local variable
      if (!toc) return;

      entries.map(item => {
        const sec = item.target;
        const target = toc.querySelector(`a[href='#${sec.id}']`);
        const parent = target?.parentElement;
        if (item.isIntersecting === true) {
          target?.classList.add("cocotb-active");
          parent?.classList.add("cocotb-active");
        } else {
          target?.classList.remove("cocotb-active");
          parent?.classList.remove("cocotb-active");
        }
      });
    }

    /**
     * Temporarily disable observer to prevent conflicts during manual navigation
     */
    temporarilyDisable(ms = 1000) {
      this.disableObserver = true;
      setTimeout(() => {
        this.disableObserver = false;
      }, ms);
    }

    /**
     * Initialize the observer with nefertiti's multi-threshold approach
     */
    init() {
      // Find the TOC container - try pydata's ID first, then fallback
      this.toc = document.querySelector("#pst-page-navigation-contents, .bd-toc nav, .bd-sidebar-secondary nav");
      if (!this.toc) {
        console.log('[Cocotb TOC] No TOC container found');
        return;
      }

      // Get header height for rootMargin calculation
      const header = document.querySelector("#pst-header, .bd-header, header");
      const headerHeight = header ? header.getBoundingClientRect().height : 0;

      // Create observer with nefertiti's multi-threshold approach
      const options = {
        root: null,
        rootMargin: `-${headerHeight}px 0px 0px 0px`,
        threshold: [0, 0.25, 0.5, 0.75, 1] // Multi-threshold for granular tracking
      };

      this.observer = new IntersectionObserver(this._handleIntersection, options);

      // Find all sections and dt elements to observe
      const elementsToObserve = [
        ...document.querySelectorAll('section[id]'),
        ...document.querySelectorAll('dl dt[id]')
      ];

      // Start observing
      elementsToObserve.forEach(el => {
        if (el.id) {
          this.observer.observe(el);
        }
      });

      // Remove any cocotb-active class from previous loads
      this.toc.querySelectorAll('.cocotb-active').forEach(el => {
        el.classList.remove('cocotb-active');
      });

      // Activate our observer
      cocotbObserverActive = true;

      // Handle hash changes
      this._setupHashHandling();
    }

    /**
     * Setup hash change handling
     * When user clicks a TOC link or changes URL hash, highlight that section
     */
    _setupHashHandling() {
      const syncTocHash = (hash) => {
        if (hash.length <= 1) return;

        // Remove all active states first
        this.toc.querySelectorAll('a').forEach(link => {
          link.classList.remove('active');
          link.removeAttribute('aria-current');
        });

        const tocLink = this.toc.querySelector(`a[href='${hash}']`);
        if (tocLink) {
          this.temporarilyDisable(1000);

          // Add cocotb-active to the clicked link
          tocLink.parentElement?.classList.add('cocotb-active');
          tocLink.setAttribute('aria-current', 'true');

          // Scroll TOC to show the active link if needed
          if (!this.isInViewport(tocLink)) {
            tocLink.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }
        }
      };

      // On page load
      syncTocHash(window.location.hash);

      // On hash change
      window.addEventListener('hashchange', () => {
        syncTocHash(window.location.hash);
      });

      // Handle same-hash clicks (edge case from pydata)
      window.addEventListener('click', (event) => {
        const link = event.target.closest('a');
        if (link &&
            link.hash === window.location.hash &&
            link.origin === window.location.origin) {
          syncTocHash(link.hash);
        }
      });
    }

    /**
     * Check if element is in viewport
     */
    isInViewport(element) {
      const rect = element.getBoundingClientRect();
      return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
      );
    }

    disconnect() {
      if (this.observer) {
        this.observer.disconnect();
      }
    }
  }

  // Initialize when DOM is ready
  function init() {
    // Don't run if we're on the search page or there's no main content
    if (!document.querySelector('#main-content, .bd-main')) {
      return;
    }

    const existingToc = document.querySelector("#pst-page-navigation-contents, .bd-toc nav, .bd-sidebar-secondary nav");
    if (existingToc) {
      // Remove any existing active states set by pydata
      existingToc.querySelectorAll('.active').forEach(el => {
        el.classList.remove('active');
      });
      existingToc.querySelectorAll('[aria-current]').forEach(el => {
        el.removeAttribute('aria-current');
      });
    }

    // Create and initialize our observer
    const tocObserver = new TocObserver();
    tocObserver.init();

    // Store reference for cleanup
    window.cocotbTocObserver = tocObserver;
  }

  // Run as early as possible - even before DOMContentLoaded
  if (document.readyState === 'loading') {
    // Try to disable pydata function before DOM loads
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
