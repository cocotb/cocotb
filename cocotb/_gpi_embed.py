import logging
import os
import importlib
from functools import reduce


def _filter_from_c(logger_name, level):
    return logging.getLogger(logger_name).isEnabledFor(level)


def _log_from_c(logger_name, level, filename, lineno, msg, function_name):
    """Log from the C world, allowing to insert C stack information."""
    logger = logging.getLogger(logger_name)
    if logger.isEnabledFor(level):
        record = logger.makeRecord(
            logger.name,
            level,
            filename,
            lineno,
            msg,
            None,
            None,
            function_name
        )
        logger.handle(record)


def _load_entry():
    """Gather entry point information by parsing :envar:`COCOTB_ENTRY_POINT`."""
    entry_point_str = os.environ.get("COCOTB_ENTRY", "cocotb:_initialise_testbench")
    try:
        if ":" not in entry_point_str:
            raise ValueError("Invalid COCOTB_ENTRY, missing entry function (no colon).")
        entry_module_str, entry_func_str = entry_point_str.split(":", 1)
        entry_module = importlib.import_module(entry_module_str)
        entry_func = reduce(getattr, entry_func_str.split('.'), entry_module)
    except Exception as e:
        raise RuntimeError("Failure to parse COCOTB_ENTRY ('{}')".format(entry_point_str)) from e
    entry_sim_event = getattr(entry_module, "_sim_event")
    assert callable(entry_sim_event)  # won't be called immediately, so we check now for time's sake
    return (entry_module, entry_func, entry_sim_event)
