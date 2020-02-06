# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os
import sys
import sysconfig
import logging
import distutils

from setuptools import Extension
from distutils.spawn import find_executable
from setuptools.command.build_ext import build_ext as _build_ext
from distutils.file_util import copy_file


logger = logging.getLogger(__name__)


def _get_lib_ext_name():
    """ Get name of default library file extension on given OS. """

    if os.name == "nt":
        ext_name = "dll"
    else:
        ext_name = "so"

    return ext_name


class build_ext(_build_ext):

    # Needed for Windows to not assume python module (generate interface in def file)
    def get_export_symbols(self, ext):
        return None

    # For proper cocotb library nameing, based on https://github.com/cython/cython/issues/1740
    def get_ext_filename(self, ext_name):
        """
        Like the base class method, but removes the ``.cpython-36m-x86_64-linux-gnu.`` part before the extension.

        Also replaces ``.pyd`` with ``.dll`` on windows.
        """

        filename = _build_ext.get_ext_filename(self, ext_name)

        # for the simulator python extension library, leaving suffix in place
        if "simulator" == os.path.split(ext_name)[-1]:
            return filename

        head, tail = os.path.split(filename)
        tail_split = tail.split(".")

        filename_short = os.path.join(head, tail_split[0] + "." + _get_lib_ext_name())

        # icarus requires vpl extension, gpivpi is default in Makefiles
        if "icarus" in filename:
            filename_short = filename_short.replace("libvpi.so", "gpivpi.vpl")
            filename_short = filename_short.replace("libvpi.dll", "gpivpi.vpl")

        return filename_short

    # Add extra library_dirs path
    def finalize_options(self):
        _build_ext.finalize_options(self)

        for ext in self.extensions:
            ext.library_dirs.append(
                os.path.join(self.build_lib, os.path.dirname(ext._full_name))
            )

    # copy libs into proper directory in develop
    def copy_extensions_to_source(self):
        build_py = self.get_finalized_command("build_py")
        for ext in self.extensions:
            fullname = self.get_ext_fullname(ext.name)
            filename = self.get_ext_filename(fullname)
            modpath = fullname.split(".")
            package = ".".join(modpath[:-1])
            package_dir = build_py.get_package_dir(package)
            # unlike the method from `setuptools`, we do not call `os.path.basename` here
            dest_filename = os.path.join(package_dir, filename)
            src_filename = os.path.join(self.build_lib, filename)

            os.makedirs(os.path.dirname(dest_filename), exist_ok=True)

            copy_file(
                src_filename, dest_filename, verbose=self.verbose, dry_run=self.dry_run
            )
            if ext._needs_stub:
                self.write_stub(package_dir or os.curdir, ext, True)


# Allow to load dependencies from the directory where vpi/vhpi/fli library is located on osx
def _extra_link_args(lib_name):
    if sys.platform == "darwin":
        return ["-Wl,-install_name,@loader_path/%s.so" % lib_name]
    else:
        return []


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
# TODO Add "-Wconversion" to _base_warns when fixed
_base_warns = ["-Wall", "-Wextra", "-Wcast-qual", "-Wwrite-strings"]
_cc_warns = _base_warns + ["-Wstrict-prototypes", "-Waggregate-return"]
_ccx_warns = _base_warns + ["-Wnon-virtual-dtor", "-Woverloaded-virtual"]

_extra_cc_compile_args = ["-std=gnu99"] + _cc_warns
_extra_cxx_compile_args = ["-std=c++11"] + _ccx_warns

# We need to build common libraries for each simulator to avoid issues with
# loading libraries from different directories in multi os configuration and
# cross dependencies without setting globally LD_LIBRARY_PATH or similar.
# `LIB_DIR` is used to point to this directory.
def _get_common_lib_ext(include_dir, share_lib_dir, sim_define):

    #
    #  libcocotbutils
    #
    libcocotbutils = Extension(
        os.path.join("cocotb", "libs", sim_define.lower(), "libcocotbutils"),
        include_dirs=[include_dir],
        sources=[os.path.join(share_lib_dir, "utils", "cocotb_utils.c")],
        extra_link_args=_extra_link_args("libcocotbutils"),
        extra_compile_args=_extra_cc_compile_args,
    )

    #
    #  libgpilog
    #
    python_lib_dirs = []
    if sys.platform == "darwin":
        python_lib_dirs = [sysconfig.get_config_var("LIBDIR")]

    libgpilog = Extension(
        os.path.join("cocotb", "libs", sim_define.lower(), "libgpilog"),
        include_dirs=[include_dir],
        libraries=[_get_python_lib_link(), "cocotbutils"],
        library_dirs=python_lib_dirs,
        sources=[os.path.join(share_lib_dir, "gpi_log", "gpi_logging.c")],
        extra_link_args=_extra_link_args("libgpilog"),
        extra_compile_args=_extra_cc_compile_args,
    )

    #
    #  libcocotb
    #
    libcocotb = Extension(
        os.path.join("cocotb", "libs", sim_define.lower(), "libcocotb"),
        define_macros=[("PYTHON_SO_LIB", _get_python_lib())],
        include_dirs=[include_dir],
        libraries=[_get_python_lib_link(), "gpilog", "cocotbutils"],
        library_dirs=python_lib_dirs,
        sources=[os.path.join(share_lib_dir, "embed", "gpi_embed.c")],
        extra_link_args=_extra_link_args("libcocotb"),
        extra_compile_args=_extra_cc_compile_args,
    )

    #
    #  libgpi
    #
    libgpi = Extension(
        os.path.join("cocotb", "libs", sim_define.lower(), "libgpi"),
        define_macros=[("LIB_EXT", _get_lib_ext_name()), ("SINGLETON_HANDLES", "")],
        include_dirs=[include_dir],
        libraries=["cocotbutils", "gpilog", "cocotb", "stdc++"],
        sources=[
            os.path.join(share_lib_dir, "gpi", "GpiCbHdl.cpp"),
            os.path.join(share_lib_dir, "gpi", "GpiCommon.cpp"),
        ],
        extra_link_args=_extra_link_args("libgpi"),
        extra_compile_args=_extra_cxx_compile_args,
    )

    #
    #  simulator
    #
    libsim = Extension(
        os.path.join("cocotb", "libs", sim_define.lower(), "simulator"),
        include_dirs=[include_dir],
        libraries=[_get_python_lib_link(), "cocotbutils", "gpilog", "gpi"],
        library_dirs=python_lib_dirs,
        sources=[os.path.join(share_lib_dir, "simulator", "simulatormodule.c")],
        extra_compile_args=_extra_cc_compile_args,
    )

    return [libcocotbutils, libgpilog, libcocotb, libgpi, libsim]


def _get_vpi_lib_ext(
    include_dir, share_lib_dir, sim_define, extra_lib=[], extra_lib_dir=[]
):
    libvpi = Extension(
        os.path.join("cocotb", "libs", sim_define.lower(), "libvpi"),
        define_macros=[("VPI_CHECKING", "1")] + [(sim_define, "")],
        include_dirs=[include_dir],
        libraries=["gpi", "gpilog"] + extra_lib,
        library_dirs=extra_lib_dir,
        sources=[
            os.path.join(share_lib_dir, "vpi", "VpiImpl.cpp"),
            os.path.join(share_lib_dir, "vpi", "VpiCbHdl.cpp"),
        ],
        extra_link_args=["-Wl,-rpath,$ORIGIN"],
        extra_compile_args=_extra_cxx_compile_args,
    )

    return libvpi


def _get_vhpi_lib_ext(
    include_dir, share_lib_dir, sim_define, extra_lib=[], extra_lib_dir=[]
):
    libcocotbvhpi = Extension(
        os.path.join("cocotb", "libs", sim_define.lower(), "libcocotbvhpi"),
        include_dirs=[include_dir],
        define_macros=[("VHPI_CHECKING", 1)] + [(sim_define, "")],
        libraries=["gpi", "gpilog", "stdc++"] + extra_lib,
        library_dirs=extra_lib_dir,
        sources=[
            os.path.join(share_lib_dir, "vhpi", "VhpiImpl.cpp"),
            os.path.join(share_lib_dir, "vhpi", "VhpiCbHdl.cpp"),
        ],
        extra_link_args=["-Wl,-rpath,$ORIGIN"],
        extra_compile_args=_extra_cxx_compile_args,
    )

    return libcocotbvhpi


def get_ext():

    cfg_vars = distutils.sysconfig.get_config_vars()

    if sys.platform == "darwin":
        cfg_vars["LDSHARED"] = cfg_vars["LDSHARED"].replace("-bundle", "-dynamiclib")

    share_dir = os.path.relpath(os.path.join(os.path.dirname(__file__), "share"))
    share_lib_dir = os.path.relpath(os.path.join(share_dir, "lib"))
    include_dir = os.path.relpath(os.path.join(share_dir, "include"))

    ext = []

    logger.info("Compiling interface libraries for cocotb ...")

    #
    #  Icarus Verilog
    #
    icarus_compile = True
    icarus_extra_lib = []
    icarus_extra_lib_path = []
    logger.info("Compiling libraries for Icarus Verilog")
    if os.name == "nt":
        iverilog_path = find_executable("iverilog")
        if iverilog_path is None:
            logger.warning(
                "Icarus Verilog executable not found. No VPI interface will be available."
            )
            icarus_compile = False
        else:
            icarus_path = os.path.dirname(os.path.dirname(iverilog_path))
            icarus_extra_lib = ["vpi"]
            icarus_extra_lib_path = [os.path.join(icarus_path, "lib")]

    if icarus_compile:
        ext += _get_common_lib_ext(include_dir, share_lib_dir, sim_define="ICARUS")
        icarus_vpi_ext = _get_vpi_lib_ext(
            include_dir=include_dir,
            share_lib_dir=share_lib_dir,
            sim_define="ICARUS",
            extra_lib=icarus_extra_lib,
            extra_lib_dir=icarus_extra_lib_path,
        )

        ext.append(icarus_vpi_ext)

    #
    #  Modelsim/Questa
    #
    vsim_path = find_executable("vdbg")
    modelsim_compile = True
    modelsim_extra_lib = []
    modelsim_extra_lib_path = []
    logger.info("Compiling libraries for Modelsim/Questa")
    if os.name == "nt":
        if vsim_path is None:
            logger.warning(
                "Modelsim/Questa executable (vdbg) not found. No VPI interface will be available."
            )
            modelsim_compile = False
        else:
            modelsim_bin_dir = os.path.dirname(vsim_path)
            modelsim_extra_lib = ["mtipli"]
            modelsim_extra_lib_path = [modelsim_bin_dir]

    if modelsim_compile:
        ext += _get_common_lib_ext(include_dir, share_lib_dir, sim_define="MODELSIM")
        modelsim_vpi_ext = _get_vpi_lib_ext(
            include_dir=include_dir,
            share_lib_dir=share_lib_dir,
            sim_define="MODELSIM",
            extra_lib=modelsim_extra_lib,
            extra_lib_dir=modelsim_extra_lib_path,
        )

        ext.append(modelsim_vpi_ext)

    if vsim_path is None:
        logger.warning(
            "Modelsim/Questa executable (vdbg) executable not found. No FLI interface will be available."
        )
    else:
        modelsim_dir = os.path.dirname(os.path.dirname(vsim_path))
        modelsim_include_dir = os.path.join(modelsim_dir, "include")
        mti_path = os.path.join(modelsim_include_dir, "mti.h")
        if os.path.isfile(mti_path):
            fli_ext = Extension(
                os.path.join("cocotb", "libs", "modelsim", "libfli"),
                include_dirs=[include_dir, modelsim_include_dir],
                libraries=["gpi", "gpilog", "stdc++"] + modelsim_extra_lib,
                library_dirs=modelsim_extra_lib_path,
                sources=[
                    os.path.join(share_lib_dir, "fli", "FliImpl.cpp"),
                    os.path.join(share_lib_dir, "fli", "FliCbHdl.cpp"),
                    os.path.join(share_lib_dir, "fli", "FliObjHdl.cpp"),
                ],
                extra_link_args=["-Wl,-rpath,$ORIGIN"],
                extra_compile_args=_extra_cxx_compile_args,
            )

            ext.append(fli_ext)

        else:
            logger.warning(
                "Cannot build FLI interface for Modelsim/Questa - "
                "the mti.h header for '{}' was not found at '{}'."
                .format(vsim_path, mti_path)
            )  # some Modelsim version does not include FLI.

    #
    # GHDL
    #
    if os.name == "posix":
        logger.info("Compiling libraries for GHDL")
        ext += _get_common_lib_ext(include_dir, share_lib_dir, sim_define="GHDL")
        ghdl_vpi_ext = _get_vpi_lib_ext(
            include_dir=include_dir, share_lib_dir=share_lib_dir, sim_define="GHDL"
        )
        ext.append(ghdl_vpi_ext)

    #
    # IUS
    #
    if os.name == "posix":
        logger.info("Compiling libraries for Incisive/Xcelium")
        ext += _get_common_lib_ext(include_dir, share_lib_dir, sim_define="IUS")
        ius_vpi_ext = _get_vpi_lib_ext(
            include_dir=include_dir, share_lib_dir=share_lib_dir, sim_define="IUS"
        )
        ext.append(ius_vpi_ext)

        ius_vhpi_ext = _get_vhpi_lib_ext(
            include_dir=include_dir, share_lib_dir=share_lib_dir, sim_define="IUS"
        )
        ext.append(ius_vhpi_ext)

    #
    # VCS
    #
    if os.name == "posix":
        logger.info("Compiling libraries for VCS")
        ext += _get_common_lib_ext(include_dir, share_lib_dir, sim_define="VCS")
        vcs_vpi_ext = _get_vpi_lib_ext(
            include_dir=include_dir, share_lib_dir=share_lib_dir, sim_define="VCS"
        )
        ext.append(vcs_vpi_ext)

    #
    # Aldec
    #
    vsimsa_path = find_executable("vsimsa")
    logger.info("Compiling libraries for Riviera")
    if vsimsa_path is None:
        logger.warning(
            "Riviera executable (vsimsa) not found. No VPI/VHPI interface will be available."
        )
    else:
        ext += _get_common_lib_ext(include_dir, share_lib_dir, sim_define="ALDEC")
        aldec_path = os.path.dirname(vsimsa_path)
        aldec_extra_lib = ["aldecpli"]
        aldec_extra_lib_path = [aldec_path]

        aldec_vpi_ext = _get_vpi_lib_ext(
            include_dir=include_dir,
            share_lib_dir=share_lib_dir,
            sim_define="ALDEC",
            extra_lib=aldec_extra_lib,
            extra_lib_dir=aldec_extra_lib_path,
        )
        ext.append(aldec_vpi_ext)

        aldec_vhpi_ext = _get_vhpi_lib_ext(
            include_dir=include_dir,
            share_lib_dir=share_lib_dir,
            sim_define="ALDEC",
            extra_lib=aldec_extra_lib,
            extra_lib_dir=aldec_extra_lib_path,
        )
        ext.append(aldec_vhpi_ext)

    #
    # Verilator
    #
    if os.name == "posix":
        logger.info("Compiling libraries for Verilator")
        ext += _get_common_lib_ext(include_dir, share_lib_dir, sim_define="VERILATOR")
        verilator_vpi_ext = _get_vpi_lib_ext(
            include_dir=include_dir, share_lib_dir=share_lib_dir, sim_define="VERILATOR"
        )
        ext.append(verilator_vpi_ext)

    return ext
