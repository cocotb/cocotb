import os

import pytest

from cocotb_tools.runner import get_runner

@pytest.mark.parametrize("val, expected", [("1", True), ("", False), ("0", False)])
def test_runner_booleans(val, expected):
    runner = get_runner("riviera")
    os.environ["EXISTING"] = val
    assert runner._get_env_var_as_bool("EXISTING", False) is expected

def test_runner_env_var_undefined():
    runner = get_runner("riviera")
    assert runner._get_env_var_as_bool("NOT_EXISTING", True) is True
