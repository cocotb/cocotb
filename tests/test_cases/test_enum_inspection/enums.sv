// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

typedef enum bit [3:0] {
    BVEC_A = 4'b0001,
    BVEC_B = 4'b0010,
    BVEC_C = 4'b0100
} bit_vec_enum_e;

typedef enum logic [3:0] {
    LVEC_A = 4'b0001,
    LVEC_B = 4'b0010,
    LVEC_C = 4'b0100
} logic_vec_enum_e;

typedef enum int {
    INT_A = 0,
    INT_B = 45,
    INT_C = -7
} int_enum_e;

typedef enum byte {
    BYTE_A = 0,
    BYTE_B = 3,
    BYTE_C = -1
} byte_enum_e;

// Anonymous enum: typedef name is empty but vpiEnumTypespec should still
// resolve.
typedef enum {
    DEF_A,
    DEF_B,
    DEF_C
} default_enum_e;

module top;

    bit_vec_enum_e   bvec_enum_signal;
    logic_vec_enum_e lvec_enum_signal;
    int_enum_e       int_enum_signal;
    byte_enum_e      byte_enum_signal;
    default_enum_e   default_enum_signal;

    // A non-enum signal so the inspector logs a (not-an-enum) line too.
    logic [7:0] plain_logic_signal;

    initial begin
        bvec_enum_signal    = BVEC_A;
        lvec_enum_signal    = LVEC_A;
        int_enum_signal     = INT_A;
        byte_enum_signal    = BYTE_A;
        default_enum_signal = DEF_A;
        plain_logic_signal  = '0;
    end

    // Riviera-PRO optimizes the design out if it sees no scheduled events,
    // and consequently never fires cbStartOfSimulation. A toggling clock
    // keeps every simulator's scheduler alive so our VPI callback runs.
    bit dummy_clk = 0;
    always #5 dummy_clk = ~dummy_clk;

endmodule
