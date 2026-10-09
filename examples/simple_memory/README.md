# simple_memory

A small multi-bank synchronous memory DUT with a JEDEC-style command
interface (ACT / RD / WR / PRE / REFAB), verified with cocotb using a
Python golden-shadow scoreboard.

## What this example covers

The existing cocotb examples show pipelines (`adder`,
`matrix_multiplier`), single-signal DUTs (`simple_dff`, `first_steps`),
and language / signal-model bridges (`mixed_language`, `mixed_signal`,
`analog_model`). None of them exercise the shape common to memory-,
cache-, and register-file-style verification:

| Pattern | Covered by existing examples | Covered here |
|---|---|---|
| Address-indexed storage DUT | — | 4 banks × 16 rows × 16 columns |
| Persistent golden reference (shadow) | — | Python `dict` per bank, checked on every read |
| Bank-partitioned state | — | 4 independent bank state machines |
| Multi-transaction scoreboarding | — | Every read verified against the shadow |

The DUT is deliberately small (4 banks, 4-bit row/column, BL1) so the
example stays digestible, but the shape mirrors what a real DRAM
controller verification environment exercises: per-bank state,
ACT-before-RD/WR ordering, and the all-bank state reset that REFRESH
imposes.

## Files

- `simple_memory.sv` — the DUT. Parameterisable bank count / row / column /
  data widths, JEDEC-style 3-bit command encoding, synchronous
  single-cycle reads.
- `test_simple_memory.py` — cocotb tests exercising ACT/RD/WR/PRE/REFAB
  with a Python-side golden model. Includes reset behavior, per-bank
  independence, and the REFAB all-bank reset invariant.
- `Makefile` — standard cocotb Makefile.

## Running

```
make
```

Default simulator is Icarus Verilog; override with `SIM=verilator`,
`SIM=questa`, etc. per the [cocotb quickstart](https://docs.cocotb.org/en/stable/quickstart.html).
