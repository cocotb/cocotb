# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os
import subprocess
from pathlib import Path

tests_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_cocotb_clean():
    path_default = Path(os.path.join("sim_build"))
    path_single = Path(os.path.join("single_dir"))
    path_multi = Path(os.path.join("first_dir/second_dir/third_dir"))

    path_default.mkdir(exist_ok=True)
    path_single.mkdir(exist_ok=True)
    path_multi.mkdir(exist_ok=True, parents=True)

    # Let's remove them one by one and assert the rest
    subprocess.check_output(["cocotb-clean"])
    assert not os.path.isdir(path_default)
    assert os.path.isdir(path_single)
    assert os.path.isdir(path_multi)

    subprocess.check_output(["cocotb-clean", "-d", "single_dir"])
    assert not os.path.isdir(path_single)

    subprocess.check_output(["cocotb-clean", "-rd", "third_dir"])
    assert not os.path.isdir(path_multi)


if __name__ == "__main__":
    test_cocotb_clean()
