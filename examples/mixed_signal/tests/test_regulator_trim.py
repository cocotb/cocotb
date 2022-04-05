# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

import itertools

import cocotb
from cocotb.triggers import Timer


class Regulator_TB:
    """Class for collecting testbench objects.

    Args:
        tb_hdl: The toplevel of the design-under-test.
            In this mixed cocotb/HDL testbench environment, it is the HDL testbench.
        settling_time_ns (int): Time in nanoseconds to wait before sample is taken.
    """

    def __init__(self, tb_hdl, settling_time_ns=1):
        self.tb_hdl = tb_hdl
        self.settling_time_ns = settling_time_ns
        self.analog_probe = (
            tb_hdl.i_analog_probe
        )  #: The instance name of the analog probe module.
        self._bit_toggle_stream = itertools.cycle(
            [0, 1]
        )  #: Produce bitstream that toggles between ``0`` and ``1``.

    async def get_voltage(self, node):
        """Measure voltage on *node*."""
        toggle = next(self._bit_toggle_stream)
        self.tb_hdl.i_analog_probe.node_to_probe.value = node.encode("ascii")
        self.analog_probe.probe_voltage_toggle.value = toggle
        await Timer(
            1, units="ps"
        )  # waiting time needed for the analog values to be updated
        self.tb_hdl._log.debug(
            "trim value={}: {}={:.4} V".format(
                self.tb_hdl.trim_val.value.signed_integer,
                self.analog_probe.node_to_probe.value.decode("ascii"),
                self.analog_probe.voltage.value,
            )
        )
        return self.analog_probe.voltage.value

    async def find_trim_val(self, probed_node, target_volt, trim_val_node):
        """Calculate best trimming value for *target_volt*.
        Algorithm is to measure voltage of *probed_node* at
        lowest and highest trim value,
        then calculate the slope and finally the target trim value from slope.
        Assumes a linear behaviour.

        Args:
            probed_node: The node to probe for the trimmed voltage.
            target_volt (float): The target voltage at *probed_node*.
            trim_val_node: The node to apply the trim value to.

        Yields:
            float: The calculated best value for *trim_val_node*.
        """
        # assuming two's complement
        trim_val_min = -(2 ** (trim_val_node.value.n_bits - 1))
        trim_val_max = 2 ** (trim_val_node.value.n_bits - 1) - 1
        # the actual trimming procedure:
        # minimum values
        trim_val_node.value = trim_val_min
        await Timer(self.settling_time_ns, units="ns")
        volt_min = await self.get_voltage(probed_node)
        # maximum values
        trim_val_node.value = trim_val_max
        await Timer(self.settling_time_ns, units="ns")
        volt_max = await self.get_voltage(probed_node)
        if target_volt > volt_max:
            self.tb_hdl._log.debug(
                "target_volt={} > volt_max={}, returning minimum trim value {}".format(
                    target_volt, volt_max, trim_val_max
                )
            )
            return trim_val_max
        if target_volt < volt_min:
            self.tb_hdl._log.debug(
                "target_volt={} < volt_min={}, returning maximum trim value {}".format(
                    target_volt, volt_min, trim_val_min
                )
            )
            return trim_val_min
        # do the calculation:
        slope = (trim_val_max - trim_val_min) / (volt_max - volt_min)
        target_trim = (target_volt - volt_min) * slope + trim_val_min
        return target_trim


@cocotb.test()
async def run_test(tb_hdl):
    """Run test for mixed signal simulation - automatic trimming of a voltage regulator."""

    tb_py = Regulator_TB(tb_hdl)
    node = "tb_regulator.i_regulator.vout"

    _ = await tb_py.get_voltage(
        node
    )  # NOTE: dummy read apparently needed because of $cds_get_analog_value in analog_probe

    # show automatic trimming
    target_volt = 3.013
    tb_py.tb_hdl._log.info(
        "Running trimming algorithm for target voltage {:.4} V".format(target_volt)
    )
    best_trim_float = await tb_py.find_trim_val(
        probed_node=node, target_volt=target_volt, trim_val_node=tb_py.tb_hdl.trim_val
    )
    best_trim_rounded = round(best_trim_float)
    tb_py.tb_hdl.trim_val.value = best_trim_rounded
    await Timer(tb_py.settling_time_ns, units="ns")
    trimmed_volt = await tb_py.get_voltage(node)
    tb_py.tb_hdl._log.info(
        "Best trimming value is {} "
        "--> voltage is {:.4} V (difference to target is {:.4} V)".format(
            best_trim_rounded, trimmed_volt, trimmed_volt - target_volt
        )
    )
    best_trim_rounded_exp = -1
    assert best_trim_rounded == best_trim_rounded_exp
