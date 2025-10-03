import os

import pytest

from cocotb_tools.runner import get_runner

sim = os.getenv(
    "SIM",
    "icarus" if os.getenv("HDL_TOPLEVEL_LANG", "verilog") == "verilog" else "nvc",
)

@pytest.mark.parametrize("val, expected", [("1", True), (None, False), ("0", False)])
def test_runner_booleans(val, expected):
    runner = get_runner(sim)
    os.environ["EXISTING"] = val
    assert runner._get_env_var_as_bool("EXISTING", False) is expected


def test_runner_env_var_undefined():
    runner = get_runner(sim)
    assert runner._get_env_var_as_bool("NOT_EXISTING", True) is True
