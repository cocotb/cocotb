# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
import cocotb


@cocotb.test()
async def test_system_task_passes(_):
    await cocotb.triggers.Timer(100, 'ns')


@cocotb.test(expect_fail=True)
async def test_system_task_fails(_):
    await cocotb.triggers.Timer(100, 'ns')
