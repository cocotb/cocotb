# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import cocotb
from cocotb.triggers import Timer


@cocotb.test(skip=not cocotb.SIM_NAME.lower().startswith("verilator"))
async def test_user_clock(dut):
    await Timer(100, 'us')

    assert dut.count1.value.integer == 114, "Expected count1 of 114, not {}".format(dut.count1.value.integer)
    assert dut.count2.value.integer == 47, "Expected count2 of 47, not {}".format(dut.count1.value.integer)
