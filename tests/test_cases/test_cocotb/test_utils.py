# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import pytest

import cocotb
import cocotb.utils as utils


@cocotb.test()
async def test_get_sim_steps(_):

    # test invalid round_mode specifier
    with pytest.raises(ValueError, match="^Invalid round_mode specifier: notvalid"):
        utils.get_sim_steps(1, "step", round_mode="notvalid")

    # test default, update if default changes
    with pytest.raises(ValueError):
        utils.get_sim_steps(0.5, "step")

    # test valid
    with pytest.raises(ValueError):
        utils.get_sim_steps(0.5, "step", round_mode="error")
    assert utils.get_sim_steps(24.0, "step", round_mode="error") == 24
    assert utils.get_sim_steps(1.2, "step", round_mode="floor") == 1
    assert utils.get_sim_steps(1.2, "step", round_mode="ceil") == 2
    assert utils.get_sim_steps(1.2, "step", round_mode="round") == 1
