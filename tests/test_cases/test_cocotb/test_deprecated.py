# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import warnings

import cocotb
import pytest
from cocotb.regression import TestFactory


# identifiers starting with `_` are illegal in VHDL
@cocotb.test(skip=cocotb.LANGUAGE in ("vhdl"))
async def test_id_deprecated(dut):
    with pytest.warns(DeprecationWarning):
        dut._id("_underscore_name", extended=False)


test_testfactory_deprecated_values = []


async def test_testfactory_deprecated_test(dut, a):
    test_testfactory_deprecated_values.append(a)


with warnings.catch_warnings(record=True) as tf_warns:
    warnings.simplefilter("default", category=DeprecationWarning)
    tf = TestFactory(test_testfactory_deprecated_test)

tf.add_option("a", [1, 2])
tf.generate_tests()


@cocotb.test
async def test_testfactory_deprecated(dut):
    assert "test_testfactory_deprecated_test_001" in globals()
    assert "test_testfactory_deprecated_test_002" in globals()
    assert test_testfactory_deprecated_values == [1, 2]
    assert len(tf_warns) == 1
    assert tf_warns[0].category is DeprecationWarning


@cocotb.test
async def test_runner_deprecated(_):
    with pytest.warns(DeprecationWarning):
        import cocotb.runner  # noqa: F401


@cocotb.test
async def test_config_deprecated(_):
    with pytest.warns(DeprecationWarning):
        import cocotb.config  # noqa: F401
