// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

#include <algorithm>    // min
#include <cassert>      // assert
#include <memory>       // unique_ptr

#include "Vtop.h"
#include "verilated.h"  // vluint64_t

static const int CLK1_HALFPERIOD_PS = 438000;  // 438ns
static const int CLK2_HALFPERIOD_PS = 1056000; // 1.056us

static vluint64_t next_clk1_toggle = CLK1_HALFPERIOD_PS;
static vluint64_t next_clk2_toggle = CLK2_HALFPERIOD_PS;

vluint64_t user_clock_cb(std::unique_ptr<Vtop> & topp, vluint64_t current_time) {

// Initial clock value
if (current_time == 0) {
    topp->clk1 = 0;
    topp->clk2 = 0;
} else {
    if (current_time == next_clk1_toggle) {
        topp->clk1 = !topp->clk1;
        next_clk1_toggle += CLK1_HALFPERIOD_PS;
    }
    if (current_time == next_clk2_toggle) {
        topp->clk2 = !topp->clk2;
        next_clk2_toggle += CLK2_HALFPERIOD_PS;
    }
}

auto next_time = std::min(next_clk1_toggle, next_clk2_toggle);
assert(next_time > current_time);

return next_time;
}
