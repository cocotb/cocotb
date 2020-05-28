# Build the cocotb documentation
#
# Note: this Makefile is *not* used by Read The Docs, it exec()'s the conf.py
# file directly. Hence, all special build steps here are only relevant for
# local builds, not for RTD builds. Add all build steps which should be executed
# in RTD builds as Python code into the conf.py file.
#

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = .venv/bin/sphinx-build
SOURCEDIR     = source
BUILDDIR      = build

# Put it first so that "make" without argument is like "make help".
help: .venv
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	@echo "Other targets"
	@echo "  .venv             Create virtual environment used to generate documentation"
	@echo "  rebuild_cocotb    Rebuilds the cocotb package and installs in the virtual environment"
	@echo "  clean             Deletes Sphinx-build artifacts"
	@echo "  distclean         Deletes the virtual environment and Sphinx-build artifacts"
	@echo "  help              Prints this help message"

.venv: requirements.txt
	@echo Creating Python venv for Sphinx build
	python3 -m venv .venv
	.venv/bin/pip -q install --upgrade pip
	.venv/bin/pip -q install -r requirements.txt
	.venv/bin/pip -q install -e ..

.PHONY: rebuild_cocotb
rebuild_cocotb:
	.venv/bin/pip -q install -e ..

.PHONY: clean
clean: .venv Makefile
	@$(SPHINXBUILD) -M clean "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: distclean
distclean:
	-rm -rf .venv build sphinxext/__pycache__

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
.DEFAULT:
# Dependencies for this special target are ignored by make, as discussed in
# http://stackoverflow.com/questions/26875072/dependencies-for-special-make-target-default-not-firing
# We hack around that by calling the target explicitly.
	make .venv

	. .venv/bin/activate; $(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
