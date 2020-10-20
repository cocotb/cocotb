//-----------------------------------------------------------------------------
// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause USE OF THIS
// SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
//-----------------------------------------------------------------------------

`timescale 1 ps / 1 ps

module fatal;

initial begin
    #10 $fatal(1, "This is a fatal message that finishes the test");
end

endmodule
