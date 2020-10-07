import logging
import os
import sys
import threading
from unittest.mock import patch

import pytest

import cocotb
from cocotb import check_debug_attach


def test_check_debug_attach_errors():
    """Test error cases for check_debug_attach."""
    try:
        del os.environ["COCOTB_PY_ATTACH"]
    except KeyError:
        pass

    check_debug_attach()
    assert 'debugpy' not in sys.modules

    os.environ["COCOTB_PY_ATTACH"] = 'invalidformat'
    with pytest.raises(RuntimeError, match=r"Failure to parse COCOTB_PY_ATTACH.*"):
        check_debug_attach()

    os.environ["COCOTB_PY_ATTACH"] = 'localhost:not_a_number'
    with pytest.raises(RuntimeError, match=r"Failure to parse COCOTB_PY_ATTACH.*"):
        check_debug_attach()

    os.environ["COCOTB_PY_ATTACH"] = 'fakehost:5678'
    with patch.dict(sys.modules, {'debugpy': None}):
        with pytest.raises(RuntimeError, match=r".* debugpy package is not importable.*"):
            check_debug_attach()

    with pytest.raises(RuntimeError, match=r"COCOTB_PY_ATTACH failure using.*"):
        check_debug_attach()


def test_check_debug_attach(caplog):
    caplog.set_level(logging.DEBUG)
    os.environ["COCOTB_PY_ATTACH"] = 'localhost:3456'
    cocotb.log = logging.getLogger('cocotb')

    def cancel_wait():
        import debugpy
        debugpy.wait_for_client.cancel()

    # Cancel debugpy.wait_for_client() from another thread
    cancel_timer = threading.Timer(5.0, cancel_wait)
    cancel_timer.start()

    check_debug_attach()

    cancel_timer.join()

    assert "Waiting for Python debugger attach on 127.0.0.1:3456" in caplog.messages
