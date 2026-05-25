#!/bin/bash
set -eo pipefail

# Create and activate a virtual environment.
uv venv --allow-existing --prompt cocotb-devenv .venv
. .venv/bin/activate

# Install development dependencies and build cocotb.
bear -- uv sync --dev

# Install prerequisites and development tools.
prek install --overwrite
