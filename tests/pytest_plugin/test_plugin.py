# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test the :mod:`cocotb_tools.pytest.plugin` module."""

from __future__ import annotations

from argparse import ArgumentParser

from cocotb_tools.pytest.plugin import _options_for_documentation


def test_plugin_option_for_documentation() -> None:
    """Test the :func:`cocotb_tools.pytest.plugin._options_for_documentation` function."""
    parser: ArgumentParser = _options_for_documentation()

    assert parser is not None
    assert isinstance(parser, ArgumentParser)
