# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import os

trust_inertial = bool(int(os.environ.get("COCOTB_TRUST_INERTIAL_WRITES", "0")))
