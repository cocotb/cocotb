# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os
import sys
import sysconfig
import logging
import distutils
import subprocess

from setuptools import Extension
from distutils.spawn import find_executable
from setuptools.command.build_ext import build_ext as _build_ext
from distutils.file_util import copy_file


logger = logging.getLogger(__name__)
cocotb_share_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "cocotb", "share"))


def _get_lib_ext_name():
    """ Get name of default library file extension on given OS. """

    if os.name == "nt":
        ext_name = "dll"
    else:
        ext_name = "so"

    return ext_name


class build_ext(_build_ext):
    def run(self):

        def_dir = os.path.join(cocotb_share_dir, "def")
        self._gen_import_libs(def_dir)

        super().run()

    # Needed for Windows to not assume python module (generate interface in def file)
    def get_export_symbols(self, ext):
        return None

    # For proper cocotb library naming, based on https://github.com/cython/cython/issues/1740
    def get_ext_filename(self, ext_name):
        """
        Like the base class method, but for libraries that are not python extension:
         - removes the ``.cpython-36m-x86_64-linux-gnu.`` or ``-cpython-36m.`` part before the extension
         - replaces ``.pyd`` with ``.dll`` on windows.
        """

        filename = _build_ext.get_ext_filename(self, ext_name)

        # for the simulator python extension library, leaving suffix in place
        if "simulator" == os.path.split(ext_name)[-1]:
            return filename

        head, tail = os.path.split(filename)
        tail_split = tail.split(".")

        # mingw on msys2 uses `-` as seperator
        tail_split = tail_split[0].split("-")

        filename_short = os.path.join(head, tail_split[0] + "." + _get_lib_ext_name())

        # icarus requires vpl extension
        filename_short = filename_short.replace("libcocotbvpi_icarus.so", "libcocotbvpi_icarus.vpl")
        filename_short = filename_short.replace("libcocotbvpi_icarus.dll", "libcocotbvpi_icarus.vpl")

        return filename_short

    def finalize_options(self):
        """ Like the base class method,but add extra library_dirs path. """

        super().finalize_options()

        for ext in self.extensions:
            ext.library_dirs.append(os.path.join(self.build_lib, "cocotb", "libs"))

    def copy_extensions_to_source(self):
        """ Like the base class method, but copy libs into proper directory in develop. """

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

    def _gen_import_libs(self, def_dir):
        """
        On Windows generate import libraries that contains the code required to
        load the DLL (.a) based on module definition files (.def)
        """

        if os.name == "nt":
            for sim in ["icarus", "modelsim", "aldec", "ghdl"]:
                subprocess.run(
                    [
                        "dlltool",
                        "-d",
                        os.path.join(def_dir, sim + ".def"),
                        "-l",
                        os.path.join(def_dir, "lib" + sim + ".a"),
                    ]
                )


def _extra_link_args(lib_name=None, rpaths=[]):
    """
    Add linker argument to load dependencies from the directory where vpi/vhpi/fli library is located
    On osx use `install_name`.
    Use `rpath` on all platforms
    """

    args = []
    if sys.platform == "darwin" and lib_name is not None:
        args += ["-Wl,-install_name,@rpath/%s.so" % lib_name]
    for rpath in rpaths:
        if sys.platform == "darwin":
            rpath = rpath.replace("$ORIGIN", "@loader_path")
        args += ["-Wl,-rpath,%s" % rpath]
    return args


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


def _get_common_lib_ext(include_dir, share_lib_dir):
    """
    Defines common libraries.

    All libraries go into the same directory to enable loading without modifying the library path (e.g. LD_LIBRARY_PATH).
    In Makefile `LIB_DIR` (s) is used to point to this directory.
    """

    #
    #  libcocotbutils
    #
    libcocotbutils = Extension(
        os.path.join("cocotb", "libs", "libcocotbutils"),
        include_dirs=[include_dir],
        libraries=["gpilog"],
        sources=[os.path.join(share_lib_dir, "utils", "cocotb_utils.cpp")],
        extra_link_args=_extra_link_args(lib_name="libcocotbutils", rpaths=["$ORIGIN"]),
        extra_compile_args=_extra_cxx_compile_args,
    )

    #
    #  libgpilog
    #
    python_lib_dirs = []
    if sys.platform == "darwin":
        python_lib_dirs = [sysconfig.get_config_var("LIBDIR")]

    libgpilog = Extension(
        os.path.join("cocotb", "libs", "libgpilog"),
        include_dirs=[include_dir],
        library_dirs=python_lib_dirs,
        sources=[os.path.join(share_lib_dir, "gpi_log", "gpi_logging.cpp")],
        extra_link_args=_extra_link_args(lib_name="libgpilog", rpaths=["$ORIGIN"]),
        extra_compile_args=_extra_cxx_compile_args,
    )

    #
    #  libcocotb
    #
    libcocotb = Extension(
        os.path.join("cocotb", "libs", "libcocotb"),
        define_macros=[("PYTHON_SO_LIB", _get_python_lib())],
        include_dirs=[include_dir],
        libraries=[_get_python_lib_link(), "gpilog", "cocotbutils"],
        library_dirs=python_lib_dirs,
        sources=[os.path.join(share_lib_dir, "embed", "gpi_embed.cpp")],
        extra_link_args=_extra_link_args(lib_name="libcocotb", rpaths=["$ORIGIN"] + python_lib_dirs),
        extra_compile_args=_extra_cxx_compile_args,
    )

    #
    #  libgpi
    #
    libgpi = Extension(
        os.path.join("cocotb", "libs", "libgpi"),
        define_macros=[("LIB_EXT", _get_lib_ext_name()), ("SINGLETON_HANDLES", "")],
        include_dirs=[include_dir],
        libraries=["cocotbutils", "gpilog", "cocotb", "stdc++"],
        sources=[
            os.path.join(share_lib_dir, "gpi", "GpiCbHdl.cpp"),
            os.path.join(share_lib_dir, "gpi", "GpiCommon.cpp"),
        ],
        extra_link_args=_extra_link_args(lib_name="libgpi", rpaths=["$ORIGIN"]),
        extra_compile_args=_extra_cxx_compile_args,
    )

    #
    #  simulator
    #
    libsim = Extension(
        os.path.join("cocotb", "simulator"),
        include_dirs=[include_dir],
        libraries=["cocotbutils", "gpilog", "gpi"],
        library_dirs=python_lib_dirs,
        sources=[os.path.join(share_lib_dir, "simulator", "simulatormodule.cpp")],
        extra_compile_args=_extra_cxx_compile_args,
        extra_link_args=_extra_link_args(rpaths=["$ORIGIN/libs"]),
    )

    # The libraries in this list are compiled in order of their appearance.
    # If there is a linking dependency on one library to another,
    # the linked library must be built first.
    return [libgpilog, libcocotbutils, libcocotb, libgpi, libsim]


def _get_vpi_lib_ext(
    include_dir, share_lib_dir, sim_define, extra_lib=[], extra_lib_dir=[]
):
    lib_name = "libcocotbvpi_" + sim_define.lower()
    libcocotbvpi = Extension(
        os.path.join("cocotb", "libs", lib_name),
        define_macros=[("VPI_CHECKING", "1")] + [(sim_define, "")],
        include_dirs=[include_dir],
        libraries=["gpi", "gpilog"] + extra_lib,
        library_dirs=extra_lib_dir,
        sources=[
            os.path.join(share_lib_dir, "vpi", "VpiImpl.cpp"),
            os.path.join(share_lib_dir, "vpi", "VpiCbHdl.cpp"),
        ],
        extra_link_args=_extra_link_args(lib_name=lib_name, rpaths=["$ORIGIN"]),
        extra_compile_args=_extra_cxx_compile_args,
    )

    return libcocotbvpi


def _get_vhpi_lib_ext(
    include_dir, share_lib_dir, sim_define, extra_lib=[], extra_lib_dir=[]
):
    lib_name = "libcocotbvhpi_" + sim_define.lower()
    libcocotbvhpi = Extension(
        os.path.join("cocotb", "libs", lib_name),
        include_dirs=[include_dir],
        define_macros=[("VHPI_CHECKING", 1)] + [(sim_define, "")],
        libraries=["gpi", "gpilog", "stdc++"] + extra_lib,
        library_dirs=extra_lib_dir,
        sources=[
            os.path.join(share_lib_dir, "vhpi", "VhpiImpl.cpp"),
            os.path.join(share_lib_dir, "vhpi", "VhpiCbHdl.cpp"),
        ],
        extra_link_args=_extra_link_args(lib_name=lib_name, rpaths=["$ORIGIN"]),
        extra_compile_args=_extra_cxx_compile_args,
    )

    return libcocotbvhpi


def get_ext():

    cfg_vars = distutils.sysconfig.get_config_vars()

    if sys.platform == "darwin":
        cfg_vars["LDSHARED"] = cfg_vars["LDSHARED"].replace("-bundle", "-dynamiclib")

    share_lib_dir = os.path.relpath(os.path.join(cocotb_share_dir, "lib"))
    include_dir = os.path.relpath(os.path.join(cocotb_share_dir, "include"))
    share_def_dir = os.path.relpath(os.path.join(cocotb_share_dir, "def"))

    ext = []

    logger.info("Compiling interface libraries for cocotb ...")

    ext += _get_common_lib_ext(include_dir, share_lib_dir)

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
    ext.append(icarus_vpi_ext)

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
    ext.append(modelsim_vpi_ext)

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
            lib_name = "libcocotbfli_modelsim"
            fli_ext = Extension(
                os.path.join("cocotb", "libs", lib_name),
                include_dirs=[include_dir, modelsim_include_dir],
                libraries=["gpi", "gpilog", "stdc++"] + modelsim_extra_lib,
                library_dirs=modelsim_extra_lib_path,
                sources=[
                    os.path.join(share_lib_dir, "fli", "FliImpl.cpp"),
                    os.path.join(share_lib_dir, "fli", "FliCbHdl.cpp"),
                    os.path.join(share_lib_dir, "fli", "FliObjHdl.cpp"),
                ],
                extra_link_args=_extra_link_args(lib_name=lib_name, rpaths=["$ORIGIN"]),
                extra_compile_args=_extra_cxx_compile_args,
            )

            ext.append(fli_ext)

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
    ext.append(ghdl_vpi_ext)

    #
    # IUS
    #
    if os.name == "posix":
        logger.info("Compiling libraries for Incisive/Xcelium")
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
        vcs_vpi_ext = _get_vpi_lib_ext(
            include_dir=include_dir, share_lib_dir=share_lib_dir, sim_define="VCS"
        )
        ext.append(vcs_vpi_ext)

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
        verilator_vpi_ext = _get_vpi_lib_ext(
            include_dir=include_dir, share_lib_dir=share_lib_dir, sim_define="VERILATOR"
        )
        ext.append(verilator_vpi_ext)

    return ext
