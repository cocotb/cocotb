# -*- coding: utf-8 -*-
#
# cocotb documentation build configuration file
#
# This file is execfile()d with the current directory set to its containing dir.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import datetime
import os
import subprocess
import sys
import textwrap

# Add in-tree extensions to path
sys.path.insert(0, os.path.abspath("../sphinxext"))

import cocotb
from cocotb_tools._vendor.distutils_version import LooseVersion

os.environ["SPHINX_BUILD"] = "1"

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.todo",
    "sphinx.ext.coverage",
    "sphinx.ext.imgmath",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinxcontrib.makedomain",
    "sphinx.ext.inheritance_diagram",
    "sphinxcontrib.cairosvgconverter",
    "breathe",
    "sphinx_issues",
    "sphinx_argparse_cli",
    "sphinxcontrib.spelling",
    "sphinx_design",
    "enum_tools.autoenum",
    "sphinx_codeautolink",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "ghdl": ("https://ghdl.github.io/ghdl", None),
    "scapy": ("https://scapy.readthedocs.io/en/latest", None),
    "pytest": ("https://docs.pytest.org/en/latest/", None),
    "coverage": ("https://coverage.readthedocs.io/en/latest/", None),
    "remote_pdb": ("https://python-remote-pdb.readthedocs.io/en/latest/", None),
    "cocotb19": ("https://docs.cocotb.org/en/v1.9.2/", None),
    "cocotb18": ("https://docs.cocotb.org/en/v1.8.1/", None),
    "cocotb17": ("https://docs.cocotb.org/en/v1.7.2/", None),
    "cocotb16": ("https://docs.cocotb.org/en/v1.6.2/", None),
    "cocotb15": ("https://docs.cocotb.org/en/v1.5.2/", None),
    "cocotb14": ("https://docs.cocotb.org/en/v1.4.0/", None),
    "cocotb13": ("https://docs.cocotb.org/en/v1.3.1/", None),
    "cocotb12": ("https://docs.cocotb.org/en/v1.2.0/", None),
    "cocotb11": ("https://docs.cocotb.org/en/v1.1/", None),
}

# Github repo
issues_github_path = "cocotb/cocotb"

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The suffix of source filenames.
source_suffix = {
    '.rst': 'restructuredtext'
}

# The master toctree document.
master_doc = "index"

# General information about the project.
project = "cocotb"
author = ""  # prevent printing extra "By {author}" above copyright line in HTML footer
years = f"2014-{datetime.datetime.now().year}"
copyright = f"{years}, cocotb contributors"

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The full version, including alpha/beta/rc tags.
release = cocotb.__version__
# The short X.Y version.
v_major, v_minor = LooseVersion(release).version[:2]
version = "{}.{}".format(v_major, v_minor)
# Cocotb commit ID
try:
    commit_id = (
        subprocess.check_output(["git", "rev-parse", "HEAD"]).strip().decode("ascii")
    )
except subprocess.CalledProcessError:
    commit_id = "master"

# Is this documentation build a ReadTheDocs build for a git tag, i.e., a
# release? Set the 'is_release_build' tag then, which can be used by the
# '.. only::' directive.
# https://docs.readthedocs.io/en/stable/reference/environment-variables.html
is_rtd_tag = 'READTHEDOCS' in os.environ and os.environ.get('READTHEDOCS_VERSION_TYPE', 'unknown') == 'tag'

if is_rtd_tag:
    tags.add('is_release_build')

autoclass_content = "both"

autodoc_typehints = "description"  # show type hints in the list of parameters
autodoc_typehints_description_target = "documented"

# use short "a | b" syntax for Literal types
python_display_short_literal_types = True

# Options for automatic links from code examples to reference docs
# (https://sphinx-codeautolink.readthedocs.io/)
codeautolink_warn_on_missing_inventory = True
codeautolink_warn_on_failed_resolve = True
codeautolink_autodoc_inject = True  # Inject an autolink-examples table to the end of all autodoc definitions
# import statements that are often used in code examples
codeautolink_global_preface = textwrap.dedent("""\
    import random
    import cocotb
    from cocotb.clock import *
    from cocotb.handle import *
    from cocotb.logging import *
    from cocotb.queue import *
    from cocotb.regression import *
    from cocotb.result import *
    from cocotb.task import *
    from cocotb.triggers import *
    from cocotb.utils import *
    """
)

codeautolink_custom_blocks = {
    # https://sphinx-codeautolink.readthedocs.io/en/latest/examples.html#doctest-code-blocks
    "pycon": "sphinx_codeautolink.clean_pycon",
}

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
# language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
# today = ''
# Else, today_fmt is used as the format for a strftime call.
# today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = [
    # these are compiled into a single file at build-time,
    # so there is no need to build them separately:
    "newsfragments/*.rst",
    # unused outputs from breathe:
    "generated/namespacelist.rst",
    "generated/namespace/*.rst",
]

# The reST default role (used for this markup: `text`) to use for all documents.
# default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
# add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
# add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
# show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

# A list of ignored prefixes for module index sorting.
# modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
# keep_warnings = False


# -- Options for HTML output ---------------------------------------------------

# We are using https://github.com/executablebooks/sphinx-book-theme
# Install with ``pip install sphinx-book-theme``
html_theme = "sphinx_book_theme"

# A dictionary of values to pass into the template engine’s context for all pages.
# https://pydata-sphinx-theme.readthedocs.io/en/stable/user_guide/light-dark.html#configure-default-theme-mode
html_context = {
    "default_mode": "light",
}

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    "logo": {
        "image_light": "_static/cocotb-logo.svg",
        "image_dark": "_static/cocotb-logo-dark.svg",
        "link": "https://cocotb.org",
    },
    # https://pydata-sphinx-theme.readthedocs.io/en/latest/user_guide/version-dropdown.html
    # https://pydata-sphinx-theme.readthedocs.io/en/latest/user_guide/readthedocs.html#version-switcher
    # "switcher": {
    #     "json_url": f"<...>/switcher.json",
    #     "version_match": ...,
    #     "check_switcher": False,
    #     "show_version_warning_banner": True,
    # },
    "repository_provider": "github",  # "gitlab", "github", "bitbucket"
    "repository_url": "https://github.com/cocotb/cocotb",
    "use_repository_button": True,
    # "use_edit_page_button": True,
    "use_issues_button": True,
    # "use_fullscreen_button": False,
    "home_page_in_toc": True,
    # "primary_sidebar_end": ["indices.html"],
}

# Add any paths that contain custom themes here, relative to this directory.
# html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
# html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
# html_short_title = None

# If given, this must be the name of an image file (path relative to the configuration directory)
# that is the favicon of the documentation, or a URL that points an image file for the favicon.
# Browsers use this as the icon for tabs, windows and bookmarks.
# It should be a 16-by-16 pixel icon in the PNG, SVG, GIF, or ICO file formats.
html_favicon = "_static/cocotb-favicon.svg"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
html_css_files = ["cocotb.css"]
html_js_files = ["cocotb.js"]

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
# html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
# html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
# html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
# html_additional_pages = {}

# If false, no module index is generated.
# html_domain_indices = True

# If false, no index is generated.
# html_use_index = True

# If true, the index is split into individual pages for each letter.
# html_split_index = False

# If true, links to the reST sources are added to the pages.
# html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
# html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
# html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
# html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
# html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = "cocotbdoc"


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #'papersize': 'letterpaper',
    # The font size ('10pt', '11pt' or '12pt').
    #'pointsize': '10pt',
    # Additional stuff for the LaTeX preamble.
    #'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
    ("index", "cocotb.tex", "cocotb Documentation", "cocotb contributors", "manual"),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
# latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
# latex_use_parts = False

# If true, show page references after internal links.
# latex_show_pagerefs = False

# If true, show URL addresses after external links.
# latex_show_urls = False

# Documents to append as an appendix to all manuals.
# latex_appendices = []

# If false, no module index is generated.
# latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [("index", "cocotb", "cocotb Documentation", ["cocotb contributors"], 1)]

# If true, show URL addresses after external links.
# man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (
        "index",
        "cocotb",
        "cocotb Documentation",
        "cocotb contributors",
        "cocotb",
        "Coroutine Cosimulation TestBench \
     environment for efficient verification of RTL using Python.",
        "Miscellaneous",
    ),
]

# Documents to append as an appendix to all manuals.
# texinfo_appendices = []

# If false, no module index is generated.
# texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
# texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
# texinfo_no_detailmenu = False

todo_include_todos = False

# -- Extra setup for C documentation with Doxygen and breathe ------------------
# see also https://breathe.readthedocs.io/en/latest/readthedocs.html
subprocess.run("doxygen", cwd="..")

cpp_id_attributes = ["GPI_EXPORT"]
breathe_projects = {"cocotb": "doxygen/_xml"}
breathe_default_project = "cocotb"
breathe_domain_by_extension = {
    "h": "cpp",
}
breathe_show_define_initializer = True

# -- Extra setup for spelling check --------------------------------------------

# Spelling language.
spelling_lang = "en_US"
tokenizer_lang = spelling_lang

# Location of word list.
spelling_word_list_filename = ["spelling_wordlist.txt"]
spelling_exclude_patterns = ["generated/**", "master-notes.rst"]

spelling_ignore_pypi_package_names = False
spelling_ignore_wiki_words = False
spelling_show_suggestions = True
spelling_ignore_acronyms = True

# -- Extra setup for inheritance_diagram directive which uses graphviz ---------

graphviz_output_format = "svg"

# -- Extra setup for towncrier -------------------------------------------------
# see also https://towncrier.readthedocs.io/en/actual-freaking-docs/

# we pass the name and version directly, to avoid towncrier failing to import the non-installed version
in_progress_notes = subprocess.check_output(
    ["towncrier", "--draft", "--name", "cocotb", "--version", release],
    cwd="../..",
    universal_newlines=True,
)
with open("master-notes.rst", "w") as f:
    f.write(in_progress_notes)

# -- External link helpers -----------------------------------------------------

extlinks = {
    "wikipedia": ("https://en.wikipedia.org/wiki/%s", None),
    "reposharp": ("https://github.com/cocotb/cocotb/issues/%s", "#"),
    "reposrc": (
        f"https://github.com/cocotb/cocotb/blob/{commit_id}/%s",
        None,
    ),
}
