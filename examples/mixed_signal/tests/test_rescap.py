# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

import cocotb
from cocotb.triggers import Timer
from cocotb.utils import get_sim_time

from collections import namedtuple, defaultdict

from itertools import cycle

import matplotlib.pyplot as plt

Dataset = namedtuple("Dataset", "time, voltage, current")


class ResCap_TB:
    """The testbench class for the rescap design."""
    def __init__(self, tb_hdl):
        self.tb_hdl = tb_hdl
        self.analog_probe = (
            tb_hdl.i_analog_probe
        )  #: The instance name of the analog probe module.
        self.togglestream = cycle(range(2))  # toggle between 0 and 1

    async def _get_single_sample(self, node):
        toggle = next(self.togglestream)
        self.tb_hdl.i_analog_probe.node_to_probe <= node.encode('ascii')
        self.analog_probe.probe_voltage_toggle <= toggle
        self.analog_probe.probe_current_toggle <= toggle
        await Timer(1, units="ps")  # waiting time needed for the analog values to be updated
        dataset = Dataset(
            time=get_sim_time(units="ns"),
            voltage=self.analog_probe.voltage.value,
            current=self.analog_probe.current.value * 1000.0  # in mA
        )
        self.tb_hdl._log.debug(
            "{}={:.4} V, {:.4} mA".format(
                self.analog_probe.node_to_probe.value.decode("ascii"), dataset.voltage, dataset.current
            )
        )
        return dataset

    async def get_sample_data(self, nodes, num=1, delay_ns=1):
        """For all *nodes*, get *num* samples, spaced *delay_ns* apart.

        Yields:
            list: List (*num* samples long) of :any:`Dataset` for all *nodes*.
        """
        if not isinstance(nodes, list):  # single element? make it a list
            _nodes = [nodes]
        else:
            _nodes = nodes
        datasets = defaultdict(list)
        for idx in range(num):
            for node in _nodes:
                dataset = await self._get_single_sample(node)
                datasets[node].append(dataset)
            if idx != num:
                await Timer(delay_ns, units="ns")
        return datasets

    def plot_data(self, datasets, nodes, graphfile="cocotb_plot.png"):
        """Save a charge graph of *nodes* to file *graphfile*.

        Voltage and current value are contained in *datasets*.
        """
        fig, ax_volt = plt.subplots()
        color_volt = "tab:red"
        color_curr = "tab:blue"
        ax_volt.set_title("rescap")
        ax_volt.set_xlabel("Time (ns)")
        ax_volt.set_ylabel("Voltage (V)", color=color_volt)
        ax_curr = ax_volt.twinx()  # instantiate a second axis that shares the same x-axis
        ax_curr.set_ylabel("Current (mA)", color=color_curr)  # we already handled the x-label with ax_volt

        for node in nodes:
            time, voltage, current = zip(*(datasets[node]))
            if node.endswith("vout"):
                alpha = 1.0
            else:
                alpha = 0.333
            ax_volt.plot(time, voltage, color=color_volt, alpha=alpha,
                         marker=".", markerfacecolor="black", linewidth=1, label=f"V({node})")
            ax_curr.plot(time, current, color=color_curr, alpha=alpha,
                         marker=".", markerfacecolor="black", linewidth=1, label=f"I({node})")

        ax_volt.tick_params(axis="y", labelcolor=color_volt)
        ax_curr.tick_params(axis="y", labelcolor=color_curr)
        ax_volt.axhline(linestyle=":", color="gray")

        mpl_align_yaxis(ax_volt, 0, ax_curr, 0)
        fig.tight_layout()  # otherwise the right y-label is slightly clipped
        fig.set_size_inches(11, 6)
        fig.legend(loc="upper right", bbox_to_anchor=(0.8, 0.9), frameon=False)

        self.tb_hdl._log.info(f"Writing file {graphfile}")
        fig.savefig(graphfile)


@cocotb.test()
async def run_test(tb_hdl):
    """Run test for mixed signal resistor/capacitor simulation."""

    tb_py = ResCap_TB(tb_hdl)

    nodes_to_probe = ["tb_rescap.i_rescap.vdd", "tb_rescap.i_rescap.vout"]
    # nodes_to_probe = ["tb_rescap.i_rescap.vdd", "tb_rescap.i_rescap.i_capacitor.p"]

    probedata = defaultdict(list)

    vdd = 0.0
    tb_py.tb_hdl.vdd_val <= vdd
    tb_py.tb_hdl.vss_val <= 0.0
    tb_py.tb_hdl._log.info(f"Setting vdd={vdd:.4} V")
    # dummy read appears to be necessary for the analog solver
    _ = await tb_py.get_sample_data(nodes=nodes_to_probe)

    for vdd in [5.55, -3.33]:
        tb_py.tb_hdl.vdd_val <= vdd
        tb_py.tb_hdl.vss_val <= 0.0
        tb_py.tb_hdl._log.info(f"Setting vdd={vdd:.4} V")
        data = await tb_py.get_sample_data(num=60, delay_ns=5, nodes=nodes_to_probe)
        for node in nodes_to_probe:
            probedata[node].extend(data[node])

    tb_py.plot_data(datasets=probedata, nodes=nodes_to_probe, graphfile="rescap.png")


def mpl_align_yaxis(ax1, v1, ax2, v2):
    """Adjust ax2 ylimit so that v2 in ax2 is aligned to v1 in ax1."""
    _, y1 = ax1.transData.transform((0, v1))
    _, y2 = ax2.transData.transform((0, v2))
    mpl_adjust_yaxis(ax2, (y1 - y2) / 2, v2)
    mpl_adjust_yaxis(ax1, (y2 - y1) / 2, v1)


def mpl_adjust_yaxis(ax, ydif, v):
    """Shift axis ax by ydiff, maintaining point v at the same location."""
    inv = ax.transData.inverted()
    _, dy = inv.transform((0, 0)) - inv.transform((0, ydif))
    miny, maxy = ax.get_ylim()
    miny, maxy = miny - v, maxy - v
    if -miny > maxy or (-miny == maxy and dy > 0):
        nminy = miny
        nmaxy = miny * (maxy + dy) / (miny + dy)
    else:
        nmaxy = maxy
        nminy = maxy * (miny + dy) / (maxy + dy)
    ax.set_ylim(nminy + v, nmaxy + v)
