# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

from typing import Optional

import cocotb
from cocotb.triggers import Timer
from cocotb.queue import Queue

"""
This is a Python model of an Analog Front-End (AFE) containing
a Programmable Gain Amplifier (PGA) with a selectable gain of 5.0 and 10.0
and a 13-bit Analog-to-Digital Converter (ADC) with a reference voltage of 2.0 V.

These analog models hand over data via a blocking :class:`cocotb.queue.Queue`.
"""


class PGA:
    """
    Model of a Programmable Gain Amplifier.

    *gain* is the amplification factor.
    """

    def __init__(
        self,
        gain: float = 5.0,
        in_queue: Optional[Queue] = None,
        out_queue: Optional[Queue] = None,
    ) -> None:
        self._gain = gain
        self.in_queue = in_queue
        self.out_queue = out_queue

        cocotb.start_soon(self.run())

    @property
    def gain(self) -> float:
        return self._gain

    @gain.setter
    def gain(self, val: float) -> None:
        self._gain = val

    async def run(self) -> None:
        while True:
            in_val_V = await self.in_queue.get()
            await Timer(1.0, "ns")  # delay
            await self.out_queue.put(in_val_V * self._gain)


class ADC:
    """
    Model of an Analog-to-Digital Converter.

    *ref_val_V* is the reference voltage in V, *n_bits* is the resolution in bits.
    """

    def __init__(
        self,
        ref_val_V: float = 2.0,
        n_bits: int = 13,
        in_queue: Optional[Queue] = None,
        out_queue: Optional[Queue] = None,
    ) -> None:
        self.ref_val_V = ref_val_V
        self.min_val = 0
        self.max_val = 2 ** n_bits - 1
        self.in_queue = in_queue
        self.out_queue = out_queue

        cocotb.start_soon(self.run())

    async def run(self) -> None:
        while True:
            in_val_V = await self.in_queue.get()  # sample immediately
            await Timer(1, "us")  # wait for conversion time
            out = int((in_val_V / self.ref_val_V) * self.max_val)
            if not (self.min_val <= out <= self.max_val):
                print(
                    f"Saturating measurement value {out} to [{self.min_val}:{self.max_val}]!"
                )
            await self.out_queue.put(min(max(self.min_val, out), self.max_val))


class AFE:
    """
    Model of an Analog Front-End.

    This model instantiates the sub-models PGA and ADC.
    """

    def __init__(
        self, in_queue: Optional[Queue] = None, out_queue: Optional[Queue] = None
    ) -> None:
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.pga_to_adc_queue = Queue()

        self.pga = PGA(in_queue=self.in_queue, out_queue=self.pga_to_adc_queue)
        self.adc = ADC(in_queue=self.pga_to_adc_queue, out_queue=self.out_queue)
