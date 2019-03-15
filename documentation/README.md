Cocotb documentation
====================

This directory contains the documentation of cocotb.

Build the HTML documentation to view it in a browser:

```sh
# build the HTML documentation
make html

# view it in your browser
xdg-open build/html/index.html
```

It is also possible to build the documentation as PDF file.
Building the PDFs requires a texlive installation, the example below assumes Ubuntu or Debian distributions
Replace the commands for your distribution as necessary.

```sh
# install build dependencies
apt-get install texlive

# build the PDF documentation
make latexpdf

# open the file in your PDF viewer
xdg-open build/latex/cocotb.pdf
```

To clean the build tree run

```sh
make clean

# or to clean even more build output
make distclean
```
