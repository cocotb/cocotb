#!/bin/bash
set -eo pipefail

# Create and activate a virtual environment.
python3 -m venv --prompt cocotb-devenv .venv
. .venv/bin/activate

# Install prerequisites and development tools.
pre-commit install
pip3 install nox pytest

# Install cocotb in editable mode.
bear -- pip3 install -e .
