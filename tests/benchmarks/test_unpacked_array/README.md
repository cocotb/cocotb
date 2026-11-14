<!--
Copyright cocotb contributors
Licensed under the Revised BSD License, see LICENSE for details.
SPDX-License-Identifier: BSD-3-Clause
-->

# Unpacked array writes

Run from the repository root with Icarus Verilog, a development cocotb install,
pytest and pytest-benchmark:

```sh
pytest -c /dev/null tests/benchmarks/test_unpacked_array --benchmark-json unpacked.json
```

The 32 cases cover 16- and 1024-element memories of 64-bit words, ascending and
descending ranges, zero and non-zero bounds, and both list and Array inputs.
Array inputs deliberately use different indices to check positional assignment.
First-write and repeated-write cases run in separate simulator processes, with
three fresh processes per case. The first-write case checks values immediately
after its first write; the repeated-write case checks after 100 alternating
writes. Both check values and HDL indices after the simulator applies writes.

The pytest-benchmark duration includes simulator startup and validation. For the
assignment measurements, use each benchmark's
`extra_info.assignment_samples` in the JSON output. `first_write_ns` and
`repeated_write_ns` measure the Python value setter, including write scheduling,
but exclude the subsequent simulator advance. They are not end-to-end HDL write
latencies. Inputs are constructed before measurement.

Child-handle cache counts are captured before any readback or child indexing.
Only the initially empty cache is asserted; post-write counts are observations
so a later optimization can reduce them. These counts are not a measurement of
all Python allocations or simulator memory. These tests apply no timing pass/fail
threshold. Compare runs using the same interpreter, simulator and machine.
