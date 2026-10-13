// This file is public domain, it can be freely copied without restrictions.
// SPDX-License-Identifier: CC0-1.0
//
// simple_memory: a tiny multi-bank synchronous memory with a JEDEC-style
// command interface (ACT / RD / WR / PRE / REFAB).
//
// Deliberately small — 4 banks, 8-bit addresses, BL1 — but big enough to
// demonstrate the verification patterns a real DRAM controller exercises:
// per-bank state machines, ACT-before-RD/WR ordering, and the all-bank
// reset that REFRESH imposes.

`timescale 1ns/1ns

module simple_memory #(
    parameter int N_BANKS    = 4,
    parameter int ROW_BITS   = 4,
    parameter int COL_BITS   = 4,
    parameter int DATA_WIDTH = 32
) (
    input  wire                            clk,
    input  wire                            rst_n,
    input  wire [2:0]                      cmd,    // see CMD_* localparams below
    input  wire [$clog2(N_BANKS)-1:0]      ba,
    input  wire [ROW_BITS-1:0]             addr,   // row on ACT, col on RD/WR
    input  wire [DATA_WIDTH-1:0]           wdata,
    output reg  [DATA_WIDTH-1:0]           rdata,
    output reg                             rdata_valid
);

    localparam [2:0] CMD_NOP   = 3'b000;
    localparam [2:0] CMD_ACT   = 3'b001;
    localparam [2:0] CMD_PRE   = 3'b010;
    localparam [2:0] CMD_RD    = 3'b011;
    localparam [2:0] CMD_WR    = 3'b100;
    localparam [2:0] CMD_REFAB = 3'b101;

    // Per-bank state. IDLE / ACTIVE only — refresh briefly forces all
    // banks back to IDLE in the same cycle (this example doesn't model
    // tRFC blocking; that's the job of a real controller's timing
    // checker).
    typedef enum logic { S_IDLE = 1'b0, S_ACTIVE = 1'b1 } bank_state_e;
    bank_state_e         bank_state [N_BANKS];
    logic [ROW_BITS-1:0] bank_row   [N_BANKS];

    localparam int N_ROWS = 1 << ROW_BITS;
    localparam int N_COLS = 1 << COL_BITS;
    logic [DATA_WIDTH-1:0] mem [N_BANKS][N_ROWS][N_COLS];

    integer i, r, c;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < N_BANKS; i++) begin
                bank_state[i] <= S_IDLE;
                bank_row[i]   <= '0;
                for (r = 0; r < N_ROWS; r++)
                    for (c = 0; c < N_COLS; c++)
                        mem[i][r][c] <= '0;
            end
            rdata       <= '0;
            rdata_valid <= 1'b0;
        end else begin
            rdata_valid <= 1'b0;   // default

            case (cmd)
                CMD_ACT: begin
                    bank_state[ba] <= S_ACTIVE;
                    bank_row[ba]   <= addr;
                end
                CMD_PRE: begin
                    bank_state[ba] <= S_IDLE;
                end
                CMD_RD: begin
                    if (bank_state[ba] == S_ACTIVE) begin
                        rdata       <= mem[ba][bank_row[ba]][addr[COL_BITS-1:0]];
                        rdata_valid <= 1'b1;
                    end
                end
                CMD_WR: begin
                    if (bank_state[ba] == S_ACTIVE) begin
                        mem[ba][bank_row[ba]][addr[COL_BITS-1:0]] <= wdata;
                    end
                end
                CMD_REFAB: begin
                    for (i = 0; i < N_BANKS; i++)
                        bank_state[i] <= S_IDLE;
                end
                default: ;  // NOP / reserved
            endcase
        end
    end

endmodule
