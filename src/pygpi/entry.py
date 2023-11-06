import importlib
import os
from functools import reduce
from types import ModuleType
from typing import Callable, Tuple


def load_entry() -> Tuple[ModuleType, Callable]:
    """Gather entry point information by parsing :envvar:`PYGPI_ENTRY_POINT`."""
    entry_point_str = os.environ.get(
        "PYGPI_ENTRY_POINT", "cocotb:_initialise_testbench"
    )
    try:
        if ":" not in entry_point_str:
            raise ValueError(
                "Invalid PYGPI_ENTRY_POINT, missing entry function (no colon)."
            )
        entry_module_str, entry_func_str = entry_point_str.split(":", 1)
        entry_module = importlib.import_module(entry_module_str)
        entry_func = reduce(getattr, entry_func_str.split("."), entry_module)
    except Exception as e:
        raise RuntimeError(
            "Failure to parse PYGPI_ENTRY_POINT ('{}')".format(entry_point_str)
        ) from e
    else:
        return entry_module, entry_func
