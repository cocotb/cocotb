# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os
import sys
import sysconfig
import logging
import distutils
import subprocess

from setuptools_dso import DSO, Extension, build_dso
from distutils.spawn import find_executable
from setuptools.command.build_ext import build_ext as _build_ext
from distutils.file_util import copy_file


logger = logging.getLogger(__name__)
cocotb_share_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "cocotb", "share"))


def name2file(self, dso, so=False):
    parts = dso.name.split('.')

    if parts[-1] == "cocotbvpi_icarus":
        ext = "vpi"
    else:
        ext = _get_lib_ext_name()

    if sys.platform == "win32":
        parts[-1] = parts[-1]+'.'+ext

    elif sys.platform == 'darwin':
        if so and dso.soversion is not None:
            parts[-1] = 'lib%s.%s.dylib'%(parts[-1], dso.soversion)
        else:
            parts[-1] = 'lib%s.%s'%(parts[-1], ext)

    else: # ELF
        if so and dso.soversion is not None:
            parts[-1] = 'lib%s.so.%s'%(parts[-1], dso.soversion)
        else:
            parts[-1] = 'lib%s.%s'%(parts[-1], ext)

    return os.path.join(*parts)

build_dso._name2file = name2file


def _get_lib_ext_name():
    """ Get name of default library file extension on given OS. """

    if os.name == "nt":
        ext_name = "dll"
    elif sys.platform == "darwin":
        ext_name = "dylib"
    else:
        ext_name = "so"

    return ext_name


def _get_python_lib_link():
    """ Get name of python library used for linking """

    if sys.platform == "darwin":
        ld_library = sysconfig.get_config_var("LIBRARY")
    else:
        ld_library = sysconfig.get_config_var("LDLIBRARY")

    if ld_library is not None:
        python_lib_link = os.path.splitext(ld_library)[0][3:]
    else:
        python_version = sysconfig.get_python_version().replace(".", "")
        python_lib_link = "python" + python_version

    return python_lib_link


def _get_python_lib():
    """ Get the library for embedded the python interpreter """

    if os.name == "nt":
        python_lib = _get_python_lib_link() + "." + _get_lib_ext_name()
    else:
        python_lib = "lib" + _get_python_lib_link() + "." + _get_lib_ext_name()

    return python_lib


# TODO [gh-1372]: make this work for MSVC which has a different flag syntax
_base_warns = ["-Wall", "-Wextra", "-Wcast-qual", "-Wwrite-strings", "-Wconversion"]
_ccx_warns = _base_warns + ["-Wnon-virtual-dtor", "-Woverloaded-virtual"]
_extra_cxx_compile_args = ["-std=c++11"] + _ccx_warns

# Make PRI* format macros available with C++11 compiler but older libc, e.g. on RHEL6.
_extra_cxx_compile_args += ["-D__STDC_FORMAT_MACROS"]

def dso_join(*args):
    return ".".join(args)


def _get_common_lib_ext(include_dir, share_lib_dir):

    """
    Defines common libraries.

    All libraries go into the same directory to enable loading without modifying the library path (e.g. LD_LIBRARY_PATH).
    In Makefile `LIB_DIR` (s) is used to point to this directory.
    """

    #
    #  libcocotbutils
    #
    libcocotbutils = DSO(
        dso_join("cocotb", "libs", "cocotbutils"),
        include_dirs=[include_dir],
        sources=[os.path.join(share_lib_dir, "utils", "cocotb_utils.cpp")],
        extra_compile_args=_extra_cxx_compile_args,
    )

    #
    #  libgpilog
    #
    python_lib_dirs = []
    if sys.platform == "darwin":
        python_lib_dirs = [sysconfig.get_config_var("LIBDIR")]

    python_include_dir = sysconfig.get_config_var("INCLUDEPY")

    libgpilog = DSO(
        dso_join("cocotb", "libs", "gpilog"),
        include_dirs=[include_dir, python_include_dir],
        dsos=["cocotb.libs.cocotbutils"],
        library_dirs=python_lib_dirs,
        sources=[os.path.join(share_lib_dir, "gpi_log", "gpi_logging.cpp")],
        extra_compile_args=_extra_cxx_compile_args,
    )

    #
    #  libcocotb
    #
    libcocotb = DSO(
        dso_join("cocotb", "libs", "cocotb"),
        define_macros=[("PYTHON_SO_LIB", _get_python_lib())],
        include_dirs=[include_dir, python_include_dir],
        libraries=[_get_python_lib_link()],
        dsos=["cocotb.libs.gpilog"],
        library_dirs=python_lib_dirs,
        sources=[os.path.join(share_lib_dir, "embed", "gpi_embed.cpp")],
        extra_compile_args=_extra_cxx_compile_args,
        extra_link_args=["-Wl,-rpath," + l for l in python_lib_dirs]
    )

    #
    #  libgpi
    #
    libgpi = DSO(
        dso_join("cocotb", "libs", "gpi"),
        define_macros=[("LIB_EXT", _get_lib_ext_name()), ("SINGLETON_HANDLES", "")],
        include_dirs=[include_dir],
        dsos=["cocotb.libs.cocotb"],
        libraries=["stdc++"],
        sources=[
            os.path.join(share_lib_dir, "gpi", "GpiCbHdl.cpp"),
            os.path.join(share_lib_dir, "gpi", "GpiCommon.cpp"),
        ],
        extra_compile_args=_extra_cxx_compile_args,
    )

    #
    #  simulator
    #
    libsim = Extension(
        dso_join("cocotb", "simulator"),
        include_dirs=[include_dir],
        dsos=["cocotb.libs.gpi"],
        library_dirs=python_lib_dirs,
        sources=[os.path.join(share_lib_dir, "simulator", "simulatormodule.cpp")],
        extra_compile_args=_extra_cxx_compile_args,
    )

    return [libcocotbutils, libgpilog, libcocotb, libgpi], [libsim]


def _get_vpi_lib_ext(
    include_dir, share_lib_dir, sim_define, extra_lib=[], extra_lib_dir=[]
):
    libcocotbvpi = DSO(
        dso_join("cocotb", "libs", "cocotbvpi_" + sim_define.lower()),
        define_macros=[("VPI_CHECKING", "1")] + [(sim_define, "")],
        include_dirs=[include_dir],
        dsos=["cocotb.libs.gpi"],
        libraries=extra_lib,
        library_dirs=extra_lib_dir,
        sources=[
            os.path.join(share_lib_dir, "vpi", "VpiImpl.cpp"),
            os.path.join(share_lib_dir, "vpi", "VpiCbHdl.cpp"),
        ],
        extra_compile_args=_extra_cxx_compile_args,
    )

    return libcocotbvpi


def _get_vhpi_lib_ext(
    include_dir, share_lib_dir, sim_define, extra_lib=[], extra_lib_dir=[]
):
    libcocotbvhpi = DSO(
        dso_join("cocotb", "libs", "cocotbvhpi_" + sim_define.lower()),
        include_dirs=[include_dir],
        define_macros=[("VHPI_CHECKING", 1)] + [(sim_define, "")],
        dsos=["cocotb.libs.gpi"],
        libraries=["stdc++"] + extra_lib,
        library_dirs=extra_lib_dir,
        sources=[
            os.path.join(share_lib_dir, "vhpi", "VhpiImpl.cpp"),
            os.path.join(share_lib_dir, "vhpi", "VhpiCbHdl.cpp"),
        ],
        extra_compile_args=_extra_cxx_compile_args,
    )

    return libcocotbvhpi


def get_ext():

    share_lib_dir = os.path.relpath(os.path.join(cocotb_share_dir, "lib"))
    include_dir = os.path.relpath(os.path.join(cocotb_share_dir, "include"))
    share_def_dir = os.path.relpath(os.path.join(cocotb_share_dir, "def"))

    logger.info("Compiling interface libraries for cocotb ...")

    dsos, ext = _get_common_lib_ext(include_dir, share_lib_dir)

    #
    #  Icarus Verilog
    #
    icarus_extra_lib = []
    icarus_extra_lib_path = []
    logger.info("Compiling libraries for Icarus Verilog")
    if os.name == "nt":
        icarus_extra_lib = ["icarus"]
        icarus_extra_lib_path = [share_def_dir]

    icarus_vpi_ext = _get_vpi_lib_ext(
        include_dir=include_dir,
        share_lib_dir=share_lib_dir,
        sim_define="ICARUS",
        extra_lib=icarus_extra_lib,
        extra_lib_dir=icarus_extra_lib_path,
    )
    dsos.append(icarus_vpi_ext)

    #
    #  Modelsim/Questa
    #
    modelsim_extra_lib = []
    modelsim_extra_lib_path = []
    logger.info("Compiling libraries for Modelsim/Questa")
    if os.name == "nt":
        modelsim_extra_lib = ["modelsim"]
        modelsim_extra_lib_path = [share_def_dir]

    modelsim_vpi_ext = _get_vpi_lib_ext(
        include_dir=include_dir,
        share_lib_dir=share_lib_dir,
        sim_define="MODELSIM",
        extra_lib=modelsim_extra_lib,
        extra_lib_dir=modelsim_extra_lib_path,
    )
    dsos.append(modelsim_vpi_ext)

    vsim_path = find_executable("vdbg")
    if vsim_path is None:
        logger.warning(
            "Modelsim/Questa executable (vdbg) executable not found. No FLI interface will be available."
        )
    else:
        modelsim_dir = os.path.dirname(os.path.dirname(vsim_path))
        modelsim_include_dir = os.path.join(modelsim_dir, "include")
        mti_path = os.path.join(modelsim_include_dir, "mti.h")
        if os.path.isfile(mti_path):
            fli_ext = DSO(
                dso_join("cocotb", "libs", "cocotbfli_modelsim"),
                include_dirs=[include_dir, modelsim_include_dir],
                dsos=["cocotb.libs.gpi"],
                libraries=["stdc++"] + modelsim_extra_lib,
                library_dirs=modelsim_extra_lib_path,
                sources=[
                    os.path.join(share_lib_dir, "fli", "FliImpl.cpp"),
                    os.path.join(share_lib_dir, "fli", "FliCbHdl.cpp"),
                    os.path.join(share_lib_dir, "fli", "FliObjHdl.cpp"),
                ],
                extra_compile_args=_extra_cxx_compile_args,
            )

            dsos.append(fli_ext)

        else:
            logger.warning(
                "Cannot build FLI interface for Modelsim/Questa - "
                "the mti.h header for '{}' was not found at '{}'.".format(
                    vsim_path, mti_path
                )
            )  # some Modelsim version does not include FLI.

    #
    # GHDL
    #
    ghdl_extra_lib = []
    ghdl_extra_lib_path = []
    logger.info("Compiling libraries for GHDL")
    if os.name == "nt":
        ghdl_extra_lib = ["ghdl"]
        ghdl_extra_lib_path = [share_def_dir]

    ghdl_vpi_ext = _get_vpi_lib_ext(
        include_dir=include_dir,
        share_lib_dir=share_lib_dir,
        sim_define="GHDL",
        extra_lib=ghdl_extra_lib,
        extra_lib_dir=ghdl_extra_lib_path,
    )
    dsos.append(ghdl_vpi_ext)

    #
    # IUS
    #
    if os.name == "posix":
        logger.info("Compiling libraries for Incisive/Xcelium")
        ius_vpi_ext = _get_vpi_lib_ext(
            include_dir=include_dir, share_lib_dir=share_lib_dir, sim_define="IUS"
        )
        dsos.append(ius_vpi_ext)

        ius_vhpi_ext = _get_vhpi_lib_ext(
            include_dir=include_dir, share_lib_dir=share_lib_dir, sim_define="IUS"
        )
        dsos.append(ius_vhpi_ext)

    #
    # VCS
    #
    if os.name == "posix":
        logger.info("Compiling libraries for VCS")
        vcs_vpi_ext = _get_vpi_lib_ext(
            include_dir=include_dir, share_lib_dir=share_lib_dir, sim_define="VCS"
        )
        dsos.append(vcs_vpi_ext)

    #
    # Aldec Riviera Pro
    #
    aldec_extra_lib = []
    aldec_extra_lib_path = []
    logger.info("Compiling libraries for Riviera")
    if os.name == "nt":
        aldec_extra_lib = ["aldec"]
        aldec_extra_lib_path = [share_def_dir]

    aldec_vpi_ext = _get_vpi_lib_ext(
        include_dir=include_dir,
        share_lib_dir=share_lib_dir,
        sim_define="ALDEC",
        extra_lib=aldec_extra_lib,
        extra_lib_dir=aldec_extra_lib_path,
    )
    dsos.append(aldec_vpi_ext)

    aldec_vhpi_ext = _get_vhpi_lib_ext(
        include_dir=include_dir,
        share_lib_dir=share_lib_dir,
        sim_define="ALDEC",
        extra_lib=aldec_extra_lib,
        extra_lib_dir=aldec_extra_lib_path,
    )
    dsos.append(aldec_vhpi_ext)

    #
    # Verilator
    #
    if os.name == "posix":
        logger.info("Compiling libraries for Verilator")
        verilator_vpi_ext = _get_vpi_lib_ext(
            include_dir=include_dir, share_lib_dir=share_lib_dir, sim_define="VERILATOR"
        )
        dsos.append(verilator_vpi_ext)

    return dsos, ext
