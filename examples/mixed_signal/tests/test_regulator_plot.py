# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0
from __future__ import annotations

import math

import matplotlib.pyplot as plt

import cocotb
from cocotb.triggers import Timer


@cocotb.test()
async def test_trim_vals(tb_hdl):
    """Set trim value of regulator and measure resulting voltage."""

    probed_node = "tb_regulator.i_regulator.vout"
    tb_hdl.vdd_val.value = 7.7
    tb_hdl.vss_val.value = 0.0

    probedata = []
    for trim_val in [0, 3, -5]:
        tb_hdl.trim_val.value = trim_val
        await Timer(1, unit="ns")
        trimmed_volt = await get_voltage(tb_hdl, probed_node)
        actual_trim_val = tb_hdl.trim_val.value.to_signed()
        cocotb.log.info(
            f"trim_val={actual_trim_val} results in {probed_node}={trimmed_volt:.4} V"
        )
        # sanity check: output voltage can not exceed supply
        assert tb_hdl.vss_val.value <= trimmed_volt <= tb_hdl.vdd_val.value
        probedata.append((actual_trim_val, trimmed_volt))

    plot_data(tb_hdl, datasets=probedata, graphfile="regulator.png")


async def get_voltage(tb_hdl, node):
    """Measure voltage on *node*."""
    await Timer(1, unit="ps")  # let trim_val take effect
    tb_hdl.i_analog_probe.node_to_probe.value = node.encode("ascii")
    tb_hdl.i_analog_probe.probe_voltage_toggle.value = ~int(
        tb_hdl.i_analog_probe.probe_voltage_toggle
    )
    await Timer(1, unit="ps")  # waiting time needed for the analog values to be updated
    cocotb.log.debug(
        f"Voltage on node {node} is {tb_hdl.i_analog_probe.voltage.value:.4} V"
    )
    return tb_hdl.i_analog_probe.voltage.value


def plot_data(tb_hdl, datasets, graphfile="cocotb_plot.png"):
    """Save a graph to file *graphfile*.

    Trim and voltage value are contained in *datasets*.
    """
    trim, voltage = zip(*datasets)
    trim_round = range(1, len(trim) + 1)

    fig = plt.figure()
    ax = plt.axes()
    ax.set_title(
        "Probed node: {}".format(
            tb_hdl.i_analog_probe.node_to_probe.value.decode("ascii")
        )
    )
    ax.set_ylabel("Voltage (V)")
    ax.set_ylim([0, math.ceil(max(voltage)) + 1])
    ax.step(trim_round, voltage, where="mid")
    ax.plot(trim_round, voltage, "C0o", alpha=0.5)
    for i, j, k in zip(trim_round, trim, voltage):
        ax.annotate(
            f"trim={j}",
            xy=(i, k),
            xytext=(0, 5),
            textcoords="offset points",
            ha="center",
        )
    ax.xaxis.set_major_locator(plt.NullLocator())
    ax.xaxis.set_major_formatter(plt.NullFormatter())
    fig.tight_layout()
    fig.set_size_inches(11, 6)

    cocotb.log.info(f"Writing file {graphfile}")
    fig.savefig(graphfile)
