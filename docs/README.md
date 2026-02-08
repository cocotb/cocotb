cocotb documentation
====================

This directory contains the documentation of cocotb, which is built with Doxygen and Sphinx.
The documentation is automatically built and uploaded with every pull request.
The documentation for the `master` branch can be found [here](https://docs.cocotb.org/en/development/).

`invoke docs` can be used to create an appropriate virtual environment and call `sphinx-build` to generate the HTML docs.

In addition to the Python dependencies managed by `uv`, `doxygen` must be installed.

Other invoke tasks (run with `invoke <env>`):
* `docs_linkcheck` - run the Sphinx `linkcheck` builder
* `docs_spelling` - run a spellchecker on the documentation
