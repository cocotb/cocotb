document.addEventListener("DOMContentLoaded", function () {
    if (window.location.href.includes("release_notes")) {
        document.body.classList.add("release-notes");
    }
    if (window.location.href.includes("library_reference_c.html")) {
        document.body.classList.add("no-version-badges");
    }
});
