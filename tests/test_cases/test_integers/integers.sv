// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

typedef enum {
    A,
    B,
    C = 45,
    D = 123789
} enum_e;

module top (
    input enum_e enum_input,
    input byte byte_input,
    input shortint shortint_input,
    input int int_input,
    input longint longint_input,
    input integer integer_input
);
    enum_e enum_signal;
    byte byte_signal;
    shortint shortint_signal;
    int int_signal;
    longint longint_signal;
    integer integer_signal;

/* Icarus optimizes out the undriven signals.
 * Verilator updates the signals every evaluation cycle.
 * This should work considering most event-base simulators will only run the constant
 * assignment, overwriting the signal values, if the driver values are updated, which
 * isn't a problem for our test.
 */
`ifndef VERILATOR
    assign enum_signal = enum_input;
    assign byte_signal = byte_input;
    assign shortint_signal = shortint_input;
    assign int_signal = int_input;
    assign longint_signal = longint_input;
    assign integer_signal = integer_input;
`endif  /* VERILATOR */

endmodule
