# Copyright cocotb contributors
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import logging
import random
import time
import warnings
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import cocotb
import cocotb._profiling
import cocotb._shutdown
import cocotb.handle
import cocotb.logging
import cocotb.simtime
import cocotb.simulator
from cocotb_tools import _env

log: logging.Logger


def init_package_from_simulation(argv: list[str]) -> None:
    """Initialize the cocotb package from a simulation context."""

    # Initialize subsystems
    cocotb._shutdown._init()
    cocotb.logging._init()
    cocotb._profiling._init()
    cocotb.simtime._init()

    # Set up local "cocotb" logger
    global log
    log = logging.getLogger("cocotb.initialize")

    # setup cocotb global variables
    cocotb.is_simulation = True
    cocotb.argv = argv
    cocotb.log = logging.getLogger("test")
    cocotb.log.setLevel(logging.INFO)
    cocotb.SIM_NAME = cocotb.simulator.get_simulator_product().strip()
    cocotb.SIM_VERSION = cocotb.simulator.get_simulator_version().strip()
    _process_plusargs()
    _setup_random_seed()
    _setup_root_handle()
    _process_packages()
    _start_user_coverage()

    # log info about the simulation
    log.info(
        "Initialized cocotb v%s from %s",
        cocotb.__version__,
        Path(__file__).parent.absolute(),
    )
    log.info("Running on %s version %s", cocotb.SIM_NAME, cocotb.SIM_VERSION)


def _process_plusargs() -> None:
    cocotb.plusargs = {}

    for option in cocotb.argv:
        if option.startswith("+"):
            if option.find("=") != -1:
                (name, value) = option[1:].split("=", 1)
                cocotb.plusargs[name] = value
            else:
                cocotb.plusargs[option[1:]] = True


def _process_packages() -> None:
    pkg_dict = {}

    from cocotb import simulator  # noqa: PLC0415

    pkgs = simulator.package_iterate()
    if pkgs is None:
        cocotb.packages = SimpleNamespace()
        return

    for pkg in pkgs:
        handle = cast(
            "cocotb.handle.HierarchyObject", cocotb.handle._make_sim_object(pkg)
        )
        name = handle._name

        # Icarus doesn't support named access to package objects:
        # https://github.com/steveicarus/iverilog/issues/1038
        # so we cannot lazily create handles
        if cocotb.SIM_NAME == "Icarus Verilog":
            handle._discover_all()
        pkg_dict[name] = handle

    cocotb.packages = SimpleNamespace(**pkg_dict)


def _start_user_coverage() -> None:
    enable_coverage: bool = False

    if _env.exists("COCOTB_USER_COVERAGE"):
        enable_coverage = _env.as_bool("COCOTB_USER_COVERAGE")

    elif _env.exists("COVERAGE"):
        warnings.warn(
            "COVERAGE is deprecated in favor of COCOTB_USER_COVERAGE",
            DeprecationWarning,
            stacklevel=2,
        )
        enable_coverage = _env.as_bool("COVERAGE")

    if enable_coverage:
        try:
            import coverage  # noqa: PLC0415
        except ImportError:
            raise RuntimeError(
                "Coverage collection requested but coverage module not available. Install it using `pip install coverage`."
            ) from None
        else:
            config_filepath: str = _env.as_str("COVERAGE_RCFILE")
            if not config_filepath:
                # Exclude cocotb itself from coverage collection.
                log.info(
                    "Collecting coverage of user code. No coverage config file supplied via COVERAGE_RCFILE."
                )
                cocotb_package_dir = Path(__file__).parent.absolute()
                user_coverage = coverage.coverage(
                    branch=True, omit=[f"{cocotb_package_dir}/*"]
                )
            else:
                log.info(
                    "Collecting coverage of user code. Coverage config file supplied."
                )
                # Allow the config file to handle all configuration
                user_coverage = coverage.coverage(config_file=config_filepath)
            user_coverage.start()

            def stop_user_coverage() -> None:
                user_coverage.stop()
                log.debug("Writing user coverage data")
                user_coverage.save()

            cocotb._shutdown.register(stop_user_coverage)


def _setup_random_seed() -> None:
    seed: int = int(time.time())

    if _env.exists("COCOTB_RANDOM_SEED"):
        seed = _env.as_int("COCOTB_RANDOM_SEED", seed)

    elif _env.exists("RANDOM_SEED"):
        warnings.warn(
            "RANDOM_SEED is deprecated in favor of COCOTB_RANDOM_SEED",
            DeprecationWarning,
        )
        seed = _env.as_int("RANDOM_SEED", seed)

    elif "ntb_random_seed" in cocotb.plusargs:
        warnings.warn(
            "Passing +ntb_random_seed will not be used to seed Python's random number generator in the future. "
            "Ensure you also set `COCOTB_RANDOM_SEED`.",
            FutureWarning,
        )
        seed = int(str(cocotb.plusargs["ntb_random_seed"]))

    elif "seed" in cocotb.plusargs:
        warnings.warn(
            "Passing +seed will not be used to seed Python's random number generator in the future. "
            "Ensure you also set `COCOTB_RANDOM_SEED`.",
            FutureWarning,
        )
        seed = int(str(cocotb.plusargs["seed"]))

    cocotb.RANDOM_SEED = seed
    random.seed(seed)
    log.info("Seeding Python random module with %d", seed)


def _setup_root_handle() -> None:
    root_name: str = _env.as_str("COCOTB_TOPLEVEL")

    if "." in root_name:
        # Skip any library component of the toplevel
        root_name = root_name.split(".", 1)[1]

    from cocotb import simulator  # noqa: PLC0415

    handle = simulator.get_root_handle(root_name)
    if not handle:
        raise RuntimeError(f"Can not find root handle {root_name!r}")

    cocotb.top = cocotb.handle._make_sim_object(handle)
