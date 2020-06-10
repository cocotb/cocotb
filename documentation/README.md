Cocotb documentation
====================

This directory contains the documentation of cocotb, which is built with Sphinx.
These docs are automatically built and uploaded with every commit. The built
version corresponding to the `master` branch can be found
[here](https://docs.cocotb.org/en/latest/)

`tox -e docs` cana be used to create an appropriate virtual environment and
invoke `sphinx-build` to generate the HTML docs.

In addition to the python dependencies managed by `tox`, `doxygen` must be
installed.
