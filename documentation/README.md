Cocotb documentation
====================

This directory contains the documentation of cocotb, which is built with Doxygen and Sphinx.
The documentation is automatically built and uploaded with every pull request.
The documentation for the `master` branch can be found [here](https://docs.cocotb.org/en/latest/).

`tox -e docs` can be used to create an appropriate virtual environment and
invoke `sphinx-build` to generate the HTML docs.

In addition to the Python dependencies managed by `tox`, `doxygen` must be
installed.

Other tox environments (run with `tox -e <env>`):
* `docs-linkcheck` - run the Sphinx `linkcheck` builder
* `docs-spelling` - run a spellchecker on the documentation
