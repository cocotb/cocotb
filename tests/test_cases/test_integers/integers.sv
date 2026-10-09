// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

typedef enum {
    A,
    B,
    C = 45,
    D = 123789
} enum_e;

typedef enum byte { BYTE_A, BYTE_B } enum_byte_e;
typedef enum longint { LONGINT_A, LONGINT_B } enum_longint_e;
typedef enum int unsigned { UINT_A, UINT_B } enum_uint_e;
typedef enum longint unsigned { ULONGINT_A, ULONGINT_B } enum_ulongint_e;

module top (
    input enum_e enum_input,
    input enum_byte_e enum_byte_input,
    input enum_longint_e enum_longint_input,
    input enum_uint_e enum_uint_input,
    input enum_ulongint_e enum_ulongint_input,
    input byte byte_input,
    input byte unsigned byte_unsigned_input,
    input shortint shortint_input,
    input shortint unsigned shortint_unsigned_input,
    input int int_input,
    input int unsigned int_unsigned_input,
    input longint longint_input,
    input longint unsigned longint_unsigned_input,
    input integer integer_input
);
    enum_e enum_signal;
    enum_byte_e enum_byte_signal;
    enum_longint_e enum_longint_signal;
    enum_uint_e enum_uint_signal;
    enum_ulongint_e enum_ulongint_signal;
    byte byte_signal;
    byte unsigned byte_unsigned_signal;
    shortint shortint_signal;
    shortint unsigned shortint_unsigned_signal;
    int int_signal;
    int unsigned int_unsigned_signal;
    longint longint_signal;
    longint unsigned longint_unsigned_signal;
    integer integer_signal;

/* Icarus optimizes out the undriven signals.
 * Verilator updates the signals every evaluation cycle.
 * This should work considering most event-base simulators will only run the constant
 * assignment, overwriting the signal values, if the driver values are updated, which
 * isn't a problem for our test.
 */
`ifndef VERILATOR
    assign enum_signal = enum_input;
    assign enum_byte_signal = enum_byte_input;
    assign enum_longint_signal = enum_longint_input;
    assign enum_uint_signal = enum_uint_input;
    assign enum_ulongint_signal = enum_ulongint_input;
    assign byte_signal = byte_input;
    assign byte_unsigned_signal = byte_unsigned_input;
    assign shortint_signal = shortint_input;
    assign shortint_unsigned_signal = shortint_unsigned_input;
    assign int_signal = int_input;
    assign int_unsigned_signal = int_unsigned_input;
    assign longint_signal = longint_input;
    assign longint_unsigned_signal = longint_unsigned_input;
    assign integer_signal = integer_input;
`endif  /* VERILATOR */

endmodule
