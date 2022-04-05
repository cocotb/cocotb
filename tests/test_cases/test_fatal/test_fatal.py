# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import cocotb
from cocotb.result import SimFailure
from cocotb.triggers import Timer


@cocotb.test(
    expect_error=SimFailure, skip=cocotb.SIM_NAME.lower().startswith("riviera")
)
async def test_fatal(_):
    await Timer(100, "ns")
