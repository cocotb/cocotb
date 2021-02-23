# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

import cocotb
from cocotb.triggers import Timer
import math
import matplotlib.pyplot as plt


@cocotb.test()
async def test_trim_vals(tb_hdl):
    """Set trim value of regulator and measure resulting voltage."""

    probed_node = "tb_regulator.i_regulator.vout"
    tb_hdl.vdd_val <= 7.7
    tb_hdl.vss_val <= 0.0

    probedata = []
    for trim_val in [0, 3, -5]:
        tb_hdl.trim_val <= trim_val
        await Timer(1, units="ns")
        trimmed_volt = await get_voltage(tb_hdl, probed_node)
        tb_hdl._log.info(
            "trim_val={} results in {}={:.4} V".format(
                tb_hdl.trim_val.value.signed_integer, probed_node, trimmed_volt
            )
        )
        # sanity check: output voltage can not exceed supply
        assert tb_hdl.vss_val.value <= trimmed_volt <= tb_hdl.vdd_val.value
        probedata.append((tb_hdl.trim_val.value.signed_integer, trimmed_volt))

    plot_data(tb_hdl, datasets=probedata, graphfile="regulator.png")


async def get_voltage(tb_hdl, node):
    """Measure voltage on *node*."""
    await Timer(1, units="ps")  # let trim_val take effect
    tb_hdl.i_analog_probe.node_to_probe <= node.encode("ascii")
    tb_hdl.i_analog_probe.probe_voltage_toggle <= ~int(tb_hdl.i_analog_probe.probe_voltage_toggle)
    await Timer(1, units="ps")  # waiting time needed for the analog values to be updated
    tb_hdl._log.debug("Voltage on node {} is {:.4} V".format(
        node, tb_hdl.i_analog_probe.voltage.value))
    return tb_hdl.i_analog_probe.voltage.value


def plot_data(tb_hdl, datasets, graphfile="cocotb_plot.png"):
    """Save a graph to file *graphfile*.

    Trim and voltage value are contained in *datasets*.
    """
    trim, voltage = zip(*datasets)
    trim_round = range(1, len(trim)+1)

    fig = plt.figure()
    ax = plt.axes()
    ax.set_title("Probed node: {}".format(tb_hdl.i_analog_probe.node_to_probe.value.decode("ascii")))
    ax.set_ylabel("Voltage (V)")
    ax.set_ylim([0, math.ceil(max(voltage))+1])
    ax.step(trim_round, voltage, where="mid")
    ax.plot(trim_round, voltage, 'C0o', alpha=0.5)
    for i, j, k in zip(trim_round, trim, voltage):
        ax.annotate(f"trim={j}", xy=(i, k), xytext=(0, 5), textcoords='offset points', ha='center')
    ax.xaxis.set_major_locator(plt.NullLocator())
    ax.xaxis.set_major_formatter(plt.NullFormatter())
    fig.tight_layout()
    fig.set_size_inches(11, 6)

    tb_hdl._log.info(f"Writing file {graphfile}")
    fig.savefig(graphfile)
