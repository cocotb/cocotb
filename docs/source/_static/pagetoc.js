export class TocObserver {
  constructor() {
    this.doc;
    this.toc;
    this.section_observer;
  }

  _sectionsObservationHandler = (entries) => {
    entries.map(item => {
      const sec = item.target;
      const target = this.toc.querySelector(`a[href='#${sec.id}']`);
      const parent = target?.parentElement;
      if (item.isIntersecting === true) {
        parent?.classList.add("active");
      } else {
        parent?.classList.remove("active");
      }
    });
  }

  _initializeSectionsObserver = (root_margin) => {
    this.section_observer = new IntersectionObserver(
      this._sectionsObservationHandler,
      {
        root: undefined,
        rootMargin: root_margin,
        threshold: [0, 0.25, 0.5, 0.75, 1],
      }
    );

    // For text:
    for (const element of this.doc.querySelectorAll(":scope section")) {
      this.section_observer.observe(element);
    }
    // APIs have <dl><dt>... entries listed in the TOC.
    for (const element of this.doc.querySelectorAll(":scope dl dt")) {
      this.section_observer.observe(element);
    }
  }

  init = () => {
    this.doc = document.querySelector("#content");
    this.toc = document.querySelector("#TableOfContents");
    if (this.doc == undefined || this.toc == undefined) {
      return -1;
    }

    const header_h = document.querySelector("header")?.offsetHeight;
    const root_margin = `-${header_h || 0}px 0px 0px 0px`;

    // The first link in the Toc does not point to the first
    // header. Fix that situation by reading what is the actual href
    // of the first header with class="headerlink", and then update
    // the first link in the toc.
    const document_1a = this.doc.querySelector("section a.headerlink");
    const toc_1a = this.toc.querySelector("a.reference[href='#']");
    if (document_1a != undefined && toc_1a != undefined) {
      toc_1a.setAttribute("href", document_1a.getAttribute("href"));
    }

    // Sphinx returns anchors in the toc with the class "internal"
    // and "reference". Also, it returns the first anchor with the
    // class "active", which is not what I prefer here. I want the
    // IntersectionObserver to handle what is the section active
    // in each moment. Therefore, I remove here the "active"
    // class from all anchors in the toc.
    const anchors = this.toc.querySelectorAll("a.reference");
    for (const anchor of anchors) {
      anchor.classList.remove("active");
    }

    this._initializeSectionsObserver(root_margin);
    return 0;
  }
}


export class LocationHashHandler {
  constructor() {
    this.toc = document.querySelector("#TableOfContents");
    window.addEventListener("hashchange", this.hashChanged);
    this.hashChanged();
  }

  isInViewport = (element) => {
    const rect = element.getBoundingClientRect();
    return (
      rect.top >= 0 &&
      rect.left >= 0 &&
      rect.bottom <= (
        window.innerHeight || document.documentElement.clientHeight
      ) &&
      rect.right <= (
        window.innerWidth || document.documentElement.clientWidth
      )
    );
  }

  hashChanged = (_) => {
    const anchors = this.toc?.querySelectorAll("a.reference.internal") || [];
    for (const anchor of anchors) {
      anchor.classList.remove("active");
    }

    const ubits = window.location.href.split("#");
    if (ubits.length > 1) {
      const toc_ref = `a.reference.internal[href='#${ubits[1]}']`;
      const toc_ref_elem = this.toc?.querySelector(toc_ref);
      if (toc_ref_elem) {
        toc_ref_elem.classList.add("active");
        if (!this.isInViewport(toc_ref_elem)) {
          toc_ref_elem.scrollIntoView({
            behavior: "smooth", block: "center"
          });
        }
      }
    }
  }
}
