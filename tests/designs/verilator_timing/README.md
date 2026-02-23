## Motivation

These test cases provided are meant to validate behavior of `cocotb` with `verilator` simulations, if timing statements are used in HDL code. Here, the term 'timing statements' refers to HDL statements which control the simulation time. The simplest example of such a statement is:

    initial begin: proc_delay
        #(10)
            clk = ~clk;
    end

Starting with Verilator 5, if timing statements are present in code, [the simulator expects the user to specify their desired method of processing timing statements with additional flags](https://veripool.org/guide/latest/exe_verilator.html#cmdoption-no-timing). This is a result of changes made to [Verilator's Model Evaluation Loop](https://veripool.org/guide/latest/connecting.html#wrappers-and-model-evaluation-loop). The issue with Verilating was first reported in [#3254](https://github.com/cocotb/cocotb/issues/3254) and fixed by PR [#verilator_timing](https://github.com/cocotb/cocotb/pull/verilator_timing).

## Test implementation
In `test_verilator_timing_[a-d].py`, 2 cocotb tests are defined: `clk_in_coroutine` and `clk_in_hdl`. The first one provides a clock generator in the coroutine, but the other one expects that a clock generator is placed in the HDL code (c.f. `test_verilator_timing.sv`). Additionally, test behavior is controlled with 2 settings: verilator's `--timing` option and `TEST_CLK_EXTERNAL` macro. The `--timing` option determines how Verilator should process timing statements. The Verilog macro is used to control whether the clock generator is present in the Verilog code. A table below summarizes all used test configurations and the expected test behavior.

### `clk_in_coroutine`

| Case  |     Flag:external_clock     | timing_option |  Clock generator  |                  Description                  |
| :---: | :-------------------------: | :-----------: | :---------------: | :-------------------------------------------: |
|   A   |            None             |     None      | HDL AND Coroutine | Expected fail: Verilator needs timing options |
|   B   | +define+TEST_CLK_EXTERNAL=1 |     None      |     Coroutine     |        Expected pass: regression case         |
|   C   |            None             |   --timing    | HDL AND Coroutine |     Expected pass: since #verilator_timing is merged      |
|   D   | +define+TEST_CLK_EXTERNAL=1 |   --timing    |     Coroutine     |        Expected pass: regression case         |

### `clk_in_hdl`

| Case  |     Flag:external_clock     | timing_option | Clock generator |                  Description                   |
| :---: | :-------------------------: | :-----------: | :-------------: | :--------------------------------------------: |
|   A   |            None             |     None      |       HDL       | Expected fail: Verilator needs timing options  |
|   B   | +define+TEST_CLK_EXTERNAL=1 |     None      |      None       | Expected fail: No events driving the simulator |
|   C   |            None             |   --timing    |       HDL       |      Expected pass: since #verilator_timing is merged      |
|   D   | +define+TEST_CLK_EXTERNAL=1 |   --timing    |      None       | Expected fail: No events driving the simulator |
