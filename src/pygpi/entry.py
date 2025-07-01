import importlib
import os
from functools import reduce
from typing import Any, Callable, List, Tuple, cast


def load_entry(argv: List[str]) -> None:
    """Gather entry point information by parsing :envvar:`PYGPI_USERS`."""

    entry_point_str = os.environ.get(
        "PYGPI_USERS",
        ",".join(
            (
                "cocotb_tools._coverage:start_cocotb_library_coverage",
                "cocotb.logging:_init",
                "cocotb.logging:_setup_formatter",
                "cocotb._init:init_package_from_simulation",
                "cocotb._init:run_regression",
            )
        ),
    )

    # Parse the entry point string of the form "module:func,module:func,...".
    # Any failure prevents any entry points from being loaded.
    entry_points: List[Tuple[str, str]] = []
    try:
        entry_points_str = entry_point_str.split(",")
        for entry_point_str in entry_points_str:
            entry_module_str, entry_func_str = entry_point_str.split(":")
            # TODO maybe some basic validation of the module and function names.
            # WITHOUT IMPORTING THEM.
            entry_points.append((entry_module_str, entry_func_str))
    except Exception as e:
        raise RuntimeError(f"Failure to parse PYGPI_USERS ('{entry_point_str}')") from e

    # Run all entry points.
    # Expect failure to stop the loading of any additional entry points.
    for entry_module_str, entry_func_str in entry_points:
        entry_module = importlib.import_module(entry_module_str)
        entry_func: Callable[[List[str]], object] = reduce(
            getattr, entry_func_str.split("."), cast("Any", entry_module)
        )
        entry_func(argv)
