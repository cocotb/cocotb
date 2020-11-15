//-----------------------------------------------------------------------------
// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause USE OF THIS
// SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
//-----------------------------------------------------------------------------

`timescale 1 ns / 1 ps

module test_end_system_tasks;

initial begin
    #10ns $cocotb_pass_test();
    #10ns $cocotb_fail_test();
end

endmodule
