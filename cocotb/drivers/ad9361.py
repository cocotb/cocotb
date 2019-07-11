# Created on Aug 24, 2014
# 
# @author: msnook

import cocotb
from cocotb.triggers import Timer, RisingEdge, Event
from cocotb.drivers import BusDriver
from cocotb.binary import BinaryValue, BinaryRepresentation

from collections import deque


class AD9361(BusDriver):
    """Driver for the AD9361 RF Transceiver."""

    def __init__(self, dut, rx_channels=1, tx_channels=1,
                 tx_clock_half_period=16276, rx_clock_half_period=16276,
                 loopback_queue_maxlen=16):
        self.dut = dut
        self.tx_clock_half_period = tx_clock_half_period
        self.rx_clock_half_period = rx_clock_half_period
        self.rx_frame_asserted = False
        self.tx_frame_asserted = False
        self.lbqi = deque()
        self.lbqq = deque()
        cocotb.fork(self._rx_clock())
        self.got_tx = Event("Got tx event")

    @cocotb.coroutine
    def _rx_clock(self):
        t = Timer(self.rx_clock_half_period)
        while True:
            self.dut.rx_clk_in_p <= 1
            self.dut.rx_clk_in_n <= 0
            yield t
            self.dut.rx_clk_in_p <= 0
            self.dut.rx_clk_in_n <= 1
            yield t

    def send_data(self, i_data, q_data, i_data2=None, q_data2=None,
                  binaryRepresentation=BinaryRepresentation.TWOS_COMPLEMENT):
        """Forks the ``rx_data_to_ad9361`` coroutine to send data.

        Args:
            i_data (int): Data of the I0 channel.
            q_data (int): Data of the Q0 channel.
            i_data2 (int, optional): Data of the I1 channel.
            q_data2 (int, optional): Data of the Q1 channel.
            binaryRepresentation (BinaryRepresentation): The representation of the binary value.
                Default is :any:`TWOS_COMPLEMENT`.
        """
        print(binaryRepresentation)
        cocotb.fork(self.rx_data_to_ad9361(i_data, q_data, i_data2, q_data2,
                    binaryRepresentation))

    @cocotb.coroutine
    def rx_data_to_ad9361(self, i_data, q_data, i_data2=None, q_data2=None,
                          binaryRepresentation=BinaryRepresentation.TWOS_COMPLEMENT):
        """Receive data to AD9361.

        This is a coroutine.

        Args:
            i_data (int): Data of the I0 channel.
            q_data (int): Data of the Q0 channel.
            i_data2 (int, optional): Data of the I1 channel.
            q_data2 (int, optional): Data of the Q1 channel.
            binaryRepresentation (BinaryRepresentation): The representation of the binary value.
                Default is :any:`TWOS_COMPLEMENT`. 
       """
        i_bin_val = BinaryValue(n_bits=12, bigEndian=False,
                                binaryRepresentation=binaryRepresentation)
        q_bin_val = BinaryValue(n_bits=12, bigEndian=False,
                                binaryRepresentation=binaryRepresentation)
        index = 0
        if i_data2 is None and q_data2 is None:
            while True:
                yield RisingEdge(self.dut.rx_clk_in_p)
                if self.rx_frame_asserted:
                    self.dut.rx_data_in_p <= i_bin_val[5:0]
                    self.dut.rx_data_in_n <= ~i_bin_val[5:0]
                    self.rx_frame_asserted = False
                    self.dut.rx_frame_in_p <= 0
                    self.dut.rx_frame_in_n <= 1
                else:
                    if index < len(i_data):
                        i_bin_val.set_value(i_data[index])
                        q_bin_val.set_value(q_data[index])
                        index += 1
                    else:
                        return
                    self.dut.rx_data_in_p <= i_bin_val[11:6]
                    self.dut.rx_data_in_n <= ~i_bin_val[11:6]
                    self.rx_frame_asserted = True
                    self.dut.rx_frame_in_p <= 1
                    self.dut.rx_frame_in_n <= 0
                yield RisingEdge(self.dut.rx_clk_in_n)
                if self.rx_frame_asserted:
                    self.dut.rx_data_in_p <= q_bin_val[11:6]
                    self.dut.rx_data_in_n <= ~q_bin_val[11:6]
                else:
                    self.dut.rx_data_in_p <= q_bin_val[5:0]
                    self.dut.rx_data_in_n <= ~q_bin_val[5:0]
        else:
            I_SEND_HIGH = True
            Q_SEND_HIGH = True
            channel = 1
            while True:
                yield RisingEdge(self.dut.rx_clk_in_p)
                if I_SEND_HIGH:
                    self.dut.rx_data_in_p <= i_bin_val[11:6]
                    self.dut.rx_data_in_n <= ~i_bin_val[11:6]
                    I_SEND_HIGH = False
                    if channel == 1:
                        self.dut.rx_frame_in_p <= 1
                        self.dut.rx_frame_in_n <= 0
                    elif channel == 2:
                        self.dut.rx_frame_in_p <= 0
                        self.dut.rx_frame_in_n <= 1
                else:
                    self.dut.rx_data_in_p <= i_bin_val[5:0]
                    self.dut.rx_data_in_n <= ~i_bin_val[5:0]
                    I_SEND_HIGH = True
                yield RisingEdge(self.dut.rx_clk_in_n)
                if Q_SEND_HIGH:
                    self.dut.rx_data_in_p <= q_bin_val[5:0]
                    self.dut.rx_data_in_n <= ~q_bin_val[5:0]
                    Q_SEND_HIGH = False
                else:
                    self.dut.rx_data_in_p <= q_bin_val[11:6]
                    self.dut.rx_data_in_n <= ~q_bin_val[11:6]
                    Q_SEND_HIGH = True
                    if index < len(i_data):
                        if channel == 1:
                            i_bin_val.set_value(i_data[index])
                            q_bin_val.set_value(q_data[index])
                            channel = 2
                        elif channel == 2:
                            i_bin_val.set_value(i_data2[index])
                            q_bin_val.set_value(q_data2[index])
                            channel = 1
                            index += 1
                    else:
                        return

    @cocotb.coroutine
    def _tx_data_from_ad9361(self):
        i_bin_val = BinaryValue(n_bits=12, bigEndian=False)
        q_bin_val = BinaryValue(n_bits=12, bigEndian=False)
        while True:
            yield RisingEdge(self.dut.tx_clk_out_p)
            if self.dut.tx_frame_out_p.value.integer == 1:
                q_bin_val[11:6] = self.dut.tx_data_out_p.value.get_binstr()
            else:
                q_bin_val[5:0] = self.dut.tx_data_out_p.value.get_binstr()
            yield RisingEdge(self.dut.tx_clk_out_n)
            if self.dut.tx_frame_out_p.value.integer == 1:
                i_bin_val[11:6] = self.dut.tx_data_out_p.value.get_binstr()
            else:
                i_bin_val[5:0] = self.dut.tx_data_out_p.value.get_binstr()
                # print("i_data",i_bin_val.get_value())
                # print("q_data",q_bin_val.get_value())
                self.lbqi.append(i_bin_val)
                self.lbqq.append(q_bin_val)
                self.got_tx.set([i_bin_val, q_bin_val])

    @cocotb.coroutine
    def _ad9361_tx_to_rx_loopback(self):
        cocotb.fork(self._tx_data_from_ad9361())
        i_bin_val = BinaryValue(n_bits=12, bigEndian=False)
        q_bin_val = BinaryValue(n_bits=12, bigEndian=False)
        while True:
            yield RisingEdge(self.dut.rx_clk_in_p)
            if self.rx_frame_asserted:
                self.dut.rx_data_in_p <= i_bin_val[5:0]
                self.dut.rx_data_in_n <= ~i_bin_val[5:0]
                self.rx_frame_asserted = False
                self.dut.rx_frame_in_p <= 0
                self.dut.rx_frame_in_n <= 1
            else:
                if len(self.lbqi) > 0:
                    i_bin_val = self.lbqi.popleft()
                else:
                    i_bin_val.set_value(0)
                if len(self.lbqq) > 0:
                    q_bin_val = self.lbqq.popleft()
                else:
                    q_bin_val.set_value(0)
                self.dut.rx_data_in_p <= i_bin_val[11:6]
                self.dut.rx_data_in_n <= ~i_bin_val[11:6]
                self.rx_frame_asserted = True
                self.dut.rx_frame_in_p <= 1
                self.dut.rx_frame_in_n <= 0
            yield RisingEdge(self.dut.rx_clk_in_n)
            if self.rx_frame_asserted:
                self.dut.rx_data_in_p <= q_bin_val[11:6]
                self.dut.rx_data_in_n <= ~q_bin_val[11:6]
            else:
                self.dut.rx_data_in_p <= q_bin_val[5:0]
                self.dut.rx_data_in_n <= ~q_bin_val[5:0]

    def ad9361_tx_to_rx_loopback(self):
        """Create loopback from tx to rx.

        Forks a coroutine doing the actual task.
        """
        cocotb.fork(self._ad9361_tx_to_rx_loopback())

    def tx_data_from_ad9361(self):
        """Transmit data from AD9361.

        Forks a coroutine doing the actual task.
        """
        cocotb.fork(self._tx_data_from_ad9361())
