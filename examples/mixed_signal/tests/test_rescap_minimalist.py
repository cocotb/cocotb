# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

import cocotb
from cocotb.triggers import Timer


@cocotb.test()
async def rescap_minimalist_test(tb_hdl):
    """Mixed signal resistor/capacitor simulation, minimalistic."""

    tb_hdl.vdd_val.value = 7.7
    tb_hdl.vss_val.value = 0.0
    tb_hdl.i_analog_probe.node_to_probe.value = b"tb_rescap.i_rescap.vout"

    for toggle in [1, 0, 1, 0, 1, 0]:
        await Timer(50, units="ns")
        tb_hdl.i_analog_probe.probe_voltage_toggle.value = toggle
        tb_hdl.i_analog_probe.probe_current_toggle.value = toggle
        await Timer(
            1, units="ps"
        )  # waiting time needed for the analog values to be updated
        tb_hdl._log.info(
            "tb_hdl.i_analog_probe@{}={:.4} V  {:.4} A".format(
                tb_hdl.i_analog_probe.node_to_probe.value.decode("ascii"),
                tb_hdl.i_analog_probe.voltage.value,
                tb_hdl.i_analog_probe.current.value,
            )
        )
