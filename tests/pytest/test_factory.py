# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os
import sys
from pathlib import Path

import pytest

from cocotb.factory import Factory
from cocotb.regression import RegressionManager

# https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/#using-package-metadata
if sys.version_info < (3, 10):
    import importlib_metadata as metadata
else:
    from importlib import metadata

TEST: Path = Path(__file__).resolve()


class MyRegressionManager(RegressionManager):
    pass


class InvalidRegressionManager:
    pass


def cocotb_regression_manager() -> type[RegressionManager]:
    """Register new regression manager for cocotb."""
    return MyRegressionManager


def cocotb_regression_manager_none() -> None:
    """Register new regression manager for cocotb."""


def cocotb_regression_manager_object() -> RegressionManager:
    """Register new regression manager for cocotb."""
    return MyRegressionManager()


def cocotb_regression_manager_invalid() -> InvalidRegressionManager:
    """Register new regression manager for cocotb."""
    return InvalidRegressionManager


@pytest.fixture(name="mock_entry_points")
def mock_entry_points_fixture() -> None:
    # Setup
    entry_points = metadata.entry_points
    pythonpath = os.environ.get("PYTHONPATH", "")
    os.environ["PYTHONPATH"] = str(TEST.parent)

    def mock(**params) -> metadata.EntryPoints:
        return metadata.EntryPoints(
            (metadata.EntryPoint(name="myplugin", group="cocotb", value=TEST.stem),),
        ).select(**params)

    metadata.entry_points = mock

    # Test
    yield None

    # Teardown
    metadata.entry_points = entry_points
    os.environ["PYTHONPATH"] = pythonpath


def test_factory_create_default() -> None:
    """Test cocotb factory to create other objects."""
    obj = Factory().create(RegressionManager)

    assert obj is not None
    assert isinstance(obj, RegressionManager)
    assert not isinstance(obj, MyRegressionManager)


def test_factory_create_from_plugin_custom(mock_entry_points) -> None:
    """Test cocotb factory to create other objects using plugin facility."""
    obj = Factory().create(RegressionManager)

    assert obj is not None
    assert isinstance(obj, MyRegressionManager)


def test_factory_create_from_plugin_none(mock_entry_points) -> None:
    """Test cocotb factory to create other objects where plugin function returns None."""
    obj = Factory().create(
        RegressionManager, plugin_function="cocotb_regression_manager_none"
    )

    assert obj is not None
    assert isinstance(obj, RegressionManager)
    assert not isinstance(obj, MyRegressionManager)


def test_factory_create_from_plugin_missing(mock_entry_points) -> None:
    """Test cocotb factory to create other objects where plugin function is not available."""
    obj = Factory().create(
        RegressionManager, plugin_function="no_cocotb_regression_manager"
    )

    assert obj is not None
    assert isinstance(obj, RegressionManager)
    assert not isinstance(obj, MyRegressionManager)


def test_factory_create_from_plugin_object(mock_entry_points) -> None:
    """Test cocotb factory to create other objects where plugin function returns created object."""
    obj = Factory().create(
        RegressionManager, plugin_function="cocotb_regression_manager_object"
    )

    assert obj is not None
    assert isinstance(obj, MyRegressionManager)


def test_factory_create_from_plugin_invalid(mock_entry_points) -> None:
    """Test cocotb factory to create other objects where plugin function returns invalid class type."""
    obj = Factory().create(
        RegressionManager, plugin_function="cocotb_regression_manager_invalid"
    )

    assert obj is not None
    assert isinstance(obj, InvalidRegressionManager)
