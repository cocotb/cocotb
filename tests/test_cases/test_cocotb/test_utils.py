# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import cocotb
import cocotb.utils as utils
import pytest


@cocotb.test()
async def test_get_sim_steps(_):

    # test invalid round_mode specifier
    with pytest.raises(ValueError) as e:
        utils.get_sim_steps(1, "step", "notvalid")
    assert "invalid" in str(e).lower()

    # test default, update if default changes
    with pytest.raises(ValueError):
        utils.get_sim_steps(0.5, "step")

    # test valid
    with pytest.raises(ValueError):
        utils.get_sim_steps(0.5, "step", "error")
    assert utils.get_sim_steps(24.0, "step", "error") == 24
    assert utils.get_sim_steps(1.2, "step", "floor") == 1
    assert utils.get_sim_steps(1.2, "step", "ceil") == 2
    assert utils.get_sim_steps(1.2, "step", "round") == 1
