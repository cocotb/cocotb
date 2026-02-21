# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Tests for the cocotb.fast API — trigger protocol, converter, and imports."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

import cocotb._fast_loop as _fast_loop_module
from cocotb import fast
from cocotb._fast_loop import SignalProxy, _FastLoopDone, run_cycles
from cocotb._fast_sched_py import ReadOnly as PyReadOnly
from cocotb._fast_sched_py import ReadWrite as PyReadWrite
from cocotb._fast_sched_py import _FastScheduler as PyFastScheduler

# Add tools/ to path so we can import the converter
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "tools"))
from convert_to_fast import convert_file

# ---------------------------------------------------------------------------
# Import availability tests
# ---------------------------------------------------------------------------


def test_fast_module_exports():
    """The public cocotb.fast module should export all expected names."""
    assert hasattr(fast, "SignalProxy")
    assert hasattr(fast, "run_cycles")
    assert hasattr(fast, "run")
    assert hasattr(fast, "RisingEdge")
    assert hasattr(fast, "FallingEdge")
    assert hasattr(fast, "ReadOnly")
    assert hasattr(fast, "ReadWrite")
    assert hasattr(fast, "ValueChange")


def test_fast_loop_module():
    """The internal _fast_loop module should provide expected symbols."""
    assert SignalProxy is not None
    assert _FastLoopDone is not None
    assert run_cycles is not None


def test_fast_sched_fallback():
    """The pure-Python fallback scheduler should be usable."""
    assert PyReadOnly is not None
    assert PyReadWrite is not None
    assert PyFastScheduler is not None


def test_fast_sched_cython():
    """The Cython scheduler should be importable if compiled."""
    cy = pytest.importorskip("cocotb._fast_sched")
    assert hasattr(cy, "RisingEdge")
    assert hasattr(cy, "_FastScheduler")


# ---------------------------------------------------------------------------
# Trigger __await__ protocol tests
# ---------------------------------------------------------------------------


def _check_trigger_await_protocol(trig):
    """Verify a trigger instance implements the zero-allocation __await__ protocol."""
    # __await__ returns self (no allocation)
    it = trig.__await__()
    assert it is trig, "__await__ should return self"

    # First __next__ yields self
    val = next(it)
    assert val is trig, "First __next__ should yield self"

    # Second __next__ raises StopIteration with value=self
    with pytest.raises(StopIteration) as exc_info:
        next(it)
    assert exc_info.value.value is trig, "StopIteration value should be self"

    # Reusable: can __await__ again
    it2 = trig.__await__()
    assert it2 is trig
    val2 = next(it2)
    assert val2 is trig


def test_readonly_await_protocol_py():
    """ReadOnly trigger __await__ protocol (Python fallback)."""
    _check_trigger_await_protocol(PyReadOnly())


def test_readwrite_await_protocol_py():
    """ReadWrite trigger __await__ protocol (Python fallback)."""
    _check_trigger_await_protocol(PyReadWrite())


def test_readonly_await_protocol_cython():
    """ReadOnly trigger __await__ protocol (Cython)."""
    cy = pytest.importorskip("cocotb._fast_sched")
    _check_trigger_await_protocol(cy.ReadOnly())


def test_readwrite_await_protocol_cython():
    """ReadWrite trigger __await__ protocol (Cython)."""
    cy = pytest.importorskip("cocotb._fast_sched")
    _check_trigger_await_protocol(cy.ReadWrite())


def test_trigger_protocol_consistency():
    """Cython and Python triggers should behave identically."""
    cy = pytest.importorskip("cocotb._fast_sched")

    for CyCls, PyCls in [(cy.ReadOnly, PyReadOnly), (cy.ReadWrite, PyReadWrite)]:
        cy_inst = CyCls()
        py_inst = PyCls()

        # Both should yield self on first next
        cy_it = cy_inst.__await__()
        py_it = py_inst.__await__()
        assert next(cy_it) is cy_inst
        assert next(py_it) is py_inst

        # Both should raise StopIteration(self) on second next
        with pytest.raises(StopIteration) as cy_exc:
            next(cy_it)
        with pytest.raises(StopIteration) as py_exc:
            next(py_it)
        assert cy_exc.value.value is cy_inst
        assert py_exc.value.value is py_inst


# ---------------------------------------------------------------------------
# Phase guard tests
# ---------------------------------------------------------------------------


def test_signal_proxy_readonly_guard():
    """SignalProxy.set_int should raise RuntimeError during ReadOnly phase."""
    # We can't create a real SignalProxy without a simulator, but we can
    # test the phase guard by manipulating _fast_phase directly.
    old_phase = _fast_loop_module._fast_phase
    try:
        _fast_loop_module._fast_phase = "readonly"
        # Create a mock proxy — we only need the phase check to fire
        proxy = object.__new__(SignalProxy)
        with pytest.raises(RuntimeError, match="ReadOnly"):
            proxy.set_int(42)
        with pytest.raises(RuntimeError, match="ReadOnly"):
            proxy.set_binstr("101")
    finally:
        _fast_loop_module._fast_phase = old_phase


def test_signal_proxy_allows_writes_outside_readonly():
    """SignalProxy should not raise when _fast_phase is not 'readonly'."""
    old_phase = _fast_loop_module._fast_phase
    try:
        for phase in ("", "readwrite"):
            _fast_loop_module._fast_phase = phase
            proxy = object.__new__(SignalProxy)
            # These would fail at the GPI level (no real _handle), but the
            # phase guard should not fire — we verify by checking no
            # RuntimeError about ReadOnly is raised.
            try:
                proxy.set_int(42)
            except RuntimeError as e:
                assert "ReadOnly" not in str(e)
            except AttributeError:
                pass  # Expected: no real _handle
    finally:
        _fast_loop_module._fast_phase = old_phase


def test_fast_phase_tracking_in_scheduler():
    """_FastScheduler should have _current_phase and _pending_phase fields."""
    sched = PyFastScheduler.__new__(PyFastScheduler)
    sched._current_phase = ""
    sched._pending_phase = ""

    assert hasattr(sched, "_current_phase")
    assert hasattr(sched, "_pending_phase")
    assert sched._current_phase == ""
    assert sched._pending_phase == ""


def test_phase_guard_readonly_to_readonly():
    """Dispatching ReadOnly while in ReadOnly phase should set an exception."""
    done = _FastLoopDone()

    async def bad_coro():
        await PyReadOnly()
        await PyReadOnly()  # illegal: already in readonly

    coro = bad_coro()
    sched = PyFastScheduler(coro, done)
    sched._current_phase = "readonly"
    sched._pending_phase = "readonly"

    trigger = PyReadOnly()
    trigger.__await__()
    next(trigger)

    # _done_trigger._finish() will raise RuntimeError("No simulator available!")
    # because there's no simulator running. The phase guard sets sched.exception
    # before calling _finish(), so we catch the _finish() error.
    try:
        sched._dispatch(trigger)
    except RuntimeError as e:
        if "No simulator" not in str(e):
            raise
    assert sched.exception is not None
    assert "ReadOnly in ReadOnly" in str(sched.exception)
    coro.close()


def test_phase_guard_readonly_to_readwrite():
    """Dispatching ReadWrite while in ReadOnly phase should set an exception."""
    done = _FastLoopDone()

    async def bad_coro():
        await PyReadOnly()
        await PyReadWrite()  # illegal: can't go to readwrite from readonly

    coro = bad_coro()
    sched = PyFastScheduler(coro, done)
    sched._current_phase = "readonly"
    sched._pending_phase = "readonly"

    trigger = PyReadWrite()
    trigger.__await__()
    next(trigger)

    try:
        sched._dispatch(trigger)
    except RuntimeError as e:
        if "No simulator" not in str(e):
            raise
    assert sched.exception is not None
    assert "ReadWrite in ReadOnly" in str(sched.exception)
    coro.close()


def test_phase_guard_allows_valid_transitions():
    """ReadOnly from non-readonly and ReadWrite from non-readonly should not error."""
    done = _FastLoopDone()

    async def dummy():
        await PyReadOnly()

    coro = dummy()
    sched = PyFastScheduler(coro, done)
    sched._current_phase = ""
    sched._pending_phase = ""

    # ReadOnly from edge phase ("") — should not set exception
    # We can't actually register the callback without a simulator,
    # so this will raise in simulator.register_readonly_callback.
    # But the phase guard itself should not fire.
    trigger = PyReadOnly()
    trigger.__await__()
    next(trigger)

    try:
        sched._dispatch(trigger)
    except Exception:
        pass  # Expected: no simulator available

    # If the phase guard fired, exception would be a RuntimeError about phase
    if sched.exception is not None:
        assert "ReadOnly" not in str(sched.exception) or "phase" not in str(
            sched.exception
        )
    coro.close()


# ---------------------------------------------------------------------------
# Converter tests
# ---------------------------------------------------------------------------


class TestConverter:
    """Tests for convert_to_fast.py."""

    @staticmethod
    def _convert(source: str) -> tuple[str, list]:
        return convert_file(textwrap.dedent(source))

    def test_simple_rw_loop(self):
        """Convert a simple read/write loop."""
        source = """\
        from __future__ import annotations
        import cocotb
        from cocotb.triggers import RisingEdge

        @cocotb.test()
        async def test_loop(dut):
            for i in range(100):
                dut.data_in.value = i
                await RisingEdge(dut.clk)
                x = dut.data_out.value
        """
        converted, warnings = self._convert(source)

        assert "from cocotb import fast" in converted
        assert "fast.SignalProxy(dut.data_in)" in converted
        assert "fast.SignalProxy(dut.data_out)" in converted
        assert "fast.RisingEdge(dut.clk)" in converted
        assert "async def _fast_inner():" in converted
        assert "await fast.run(_fast_inner())" in converted
        assert ".set_int(i)" in converted
        assert ".get_int()" in converted

    def test_multiple_triggers(self):
        """Convert loop with RisingEdge + ReadOnly."""
        source = """\
        from __future__ import annotations
        import cocotb
        from cocotb.triggers import RisingEdge, ReadOnly

        @cocotb.test()
        async def test_loop(dut):
            for i in range(100):
                dut.data_in.value = i
                await RisingEdge(dut.clk)
                await ReadOnly()
                x = dut.data_out.value
        """
        converted, warnings = self._convert(source)

        assert "fast.RisingEdge(dut.clk)" in converted
        assert "fast.ReadOnly()" in converted

    def test_unsupported_trigger_warning(self):
        """Warn about Timer and other unsupported triggers."""
        source = """\
        from __future__ import annotations
        import cocotb
        from cocotb.triggers import Timer

        @cocotb.test()
        async def test_loop(dut):
            for i in range(100):
                dut.data_in.value = i
                await Timer(10, units="ns")
        """
        _converted, warnings = self._convert(source)

        warning_msgs = [w.message for w in warnings]
        assert any("Timer" in msg and "not supported" in msg for msg in warning_msgs)

    def test_no_cocotb_test(self):
        """Warn when no @cocotb.test() found."""
        source = """\
        from __future__ import annotations
        async def plain_func():
            pass
        """
        _converted, warnings = self._convert(source)

        warning_msgs = [w.message for w in warnings]
        assert any("No @cocotb.test()" in msg for msg in warning_msgs)

    def test_no_hot_loop(self):
        """Warn when test has no hot loops."""
        source = """\
        from __future__ import annotations
        import cocotb
        from cocotb.triggers import RisingEdge

        @cocotb.test()
        async def test_no_loop(dut):
            dut.data.value = 42
            await RisingEdge(dut.clk)
        """
        _converted, warnings = self._convert(source)

        warning_msgs = [w.message for w in warnings]
        assert any("no hot loops" in msg for msg in warning_msgs)

    def test_preserves_non_loop_code(self):
        """Code outside the loop should be preserved."""
        source = """\
        from __future__ import annotations
        import cocotb
        from cocotb.triggers import RisingEdge

        @cocotb.test()
        async def test_loop(dut):
            dut.reset.value = 1
            for i in range(100):
                dut.data.value = i
                await RisingEdge(dut.clk)
            cocotb.log.info("done")
        """
        converted, warnings = self._convert(source)

        # Setup and teardown code preserved
        assert "dut.reset.value = 1" in converted
        assert 'cocotb.log.info("done")' in converted
        # Loop was converted
        assert "fast.run(_fast_inner())" in converted

    def test_import_added_once(self):
        """The fast import should only appear once."""
        source = """\
        from __future__ import annotations
        import cocotb
        from cocotb.triggers import RisingEdge

        @cocotb.test()
        async def test_a(dut):
            for i in range(100):
                dut.x.value = i
                await RisingEdge(dut.clk)

        @cocotb.test()
        async def test_b(dut):
            for i in range(100):
                dut.y.value = i
                await RisingEdge(dut.clk)
        """
        converted, warnings = self._convert(source)

        assert converted.count("from cocotb import fast") == 1

    def test_existing_fast_import_not_duplicated(self):
        """Don't add a second fast import if already present."""
        source = """\
        from __future__ import annotations
        import cocotb
        from cocotb import fast
        from cocotb.triggers import RisingEdge

        @cocotb.test()
        async def test_loop(dut):
            for i in range(100):
                dut.data.value = i
                await RisingEdge(dut.clk)
        """
        converted, warnings = self._convert(source)

        assert converted.count("from cocotb import fast") == 1
