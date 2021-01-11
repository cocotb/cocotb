# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os
import sys
import sysconfig
import logging
import distutils
import subprocess
import textwrap

from setuptools import Extension
from distutils.spawn import find_executable
from setuptools.command.build_ext import build_ext as _build_ext
from distutils.file_util import copy_file
from typing import List


logger = logging.getLogger(__name__)
cocotb_share_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "cocotb", "share"))

_base_warns = ["-Wall", "-Wextra", "-Wcast-qual", "-Wwrite-strings", "-Wconversion"]
_ccx_warns = _base_warns + ["-Wnon-virtual-dtor", "-Woverloaded-virtual"]
_extra_cxx_compile_args = ["-std=c++11", "-fvisibility=hidden", "-fvisibility-inlines-hidden"] + _ccx_warns
if os.name != "nt":
    _extra_cxx_compile_args += ["-flto"]

# Make PRI* format macros available with C++11 compiler but older libc, e.g. on RHEL6.
_extra_defines = [("__STDC_FORMAT_MACROS", "")]


def create_sxs_assembly_manifest(name: str, filename: str, libraries: List[str], dependency_only=False) -> str:
    """
    Create side-by-side (sxs) assembly manifest

    It contains dependencies to other assemblies (in our case the assemblies are equal to the other libraries).
    For more details see:
     - https://docs.microsoft.com/en-us/windows/win32/sbscs/assembly-manifests
     - https://docs.microsoft.com/en-us/windows/win32/sbscs/using-side-by-side-assemblies

    Args:
        name: The name of the assembly for which the manifest is generated, e.g. ``libcocotbutils``.
        filename: The filename of the library, e.g. ``libcocotbutils.dll``.
        libraries: A list of names of dependent manifests, e.g. ``["libgpilog"]``.
    """

    architecture = "amd64" if sys.maxsize > 2**32 else "x86"
    dependencies = []

    for lib in libraries:
        dependencies.append(textwrap.dedent('''\
            <dependency>
                <dependentAssembly>
                    <assemblyIdentity name="%s" version="1.0.0.0" type="win32" processorArchitecture="%s" />
                </dependentAssembly>
            </dependency>
            ''') % (lib, architecture))

    if not dependency_only:
        manifest_body = textwrap.dedent('''\
            <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
                <assemblyIdentity name="%s" version="1.0.0.0" type="win32" processorArchitecture="%s" />
                <file name="%s" />
                %s
            </assembly>
            ''') % (name, architecture, filename, textwrap.indent("".join(dependencies), '    ').strip())
    else:
        manifest_body = textwrap.dedent('''\
            <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
                %s
            </assembly>
            ''') % (textwrap.indent("".join(dependencies), '    ').strip())

    return manifest_body


def create_sxs_appconfig(filename):
    """
    Create side-by-side (sxs) application configuration file.

    The application configuration specifies additional search paths for manifests.
    For more details see: https://docs.microsoft.com/en-us/windows/win32/sbscs/application-configuration-files
    """

    config_body = textwrap.dedent('''\
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <configuration>
            <windows>
                <assemblyBinding xmlns="urn:schemas-microsoft-com:asm.v1">
                    <probing privatePath="libs" />
                </assemblyBinding>
            </windows>
        </configuration>
        ''')

    dirpath = os.path.dirname(filename)
    os.makedirs(dirpath, exist_ok=True)

    with open(filename + ".2.config", "w", encoding='utf-8') as f:
        f.write(config_body)


def create_rc_file(name, filename, libraries):
    """
    Creates windows resource definition script to embed the side-by-side assembly manifest into the libraries.

    For more details see: https://docs.microsoft.com/en-us/windows/win32/menurc/about-resource-files
    """

    manifest = create_sxs_assembly_manifest(name, filename, libraries)

    # Escape double quotes and put every line between double quotes for embedding into rc file
    manifest = manifest.replace('"', '""')
    manifest = '\n'.join(['"%s\\r\\n"' % x for x in manifest.splitlines()])

    rc_body = textwrap.dedent('''\
        #pragma code_page(65001) // UTF-8
        #include <WinUser.h>

        LANGUAGE 0x00, 0x00

        ISOLATIONAWARE_MANIFEST_RESOURCE_ID RT_MANIFEST
        BEGIN
        %s
        END
        ''') % manifest

    # Add the runtime dependency on libcocotb to libembed dependencies
    if name == "libembed":
        manifest = create_sxs_assembly_manifest(name, filename, ["libcocotb"], dependency_only=True)

        # Escape double quotes and put every line between double quotes for embedding into rc file
        manifest = manifest.replace('"', '""')
        manifest = '\n'.join(['"%s\\r\\n"' % x for x in manifest.splitlines()])

        rc_body += textwrap.dedent('''\
            1000 RT_MANIFEST
            BEGIN
            %s
            END
            ''') % manifest

    with open(name + ".rc", "w", encoding='utf-8') as f:
        f.write(rc_body)


def _get_lib_ext_name():
    """ Get name of default library file extension on given OS. """

    if os.name == "nt":
        ext_name = "dll"
    else:
        ext_name = "so"

    return ext_name


class build_ext(_build_ext):
    def run(self):
        if os.name == "nt":
            create_sxs_appconfig(self.get_ext_fullpath(os.path.join("cocotb", "simulator")))

            ext_names = {os.path.split(ext.name)[-1] for ext in self.extensions}
            for ext in self.extensions:
                fullname = self.get_ext_fullname(ext.name)
                filename = self.get_ext_filename(fullname)
                name = os.path.split(fullname)[-1]
                filename = os.path.split(filename)[-1]
                libraries = {"lib" + lib for lib in ext.libraries}.intersection(ext_names)
                create_rc_file(name, filename, libraries)

        super().run()

    def build_extensions(self):
        if os.name == "nt":
            def_dir = os.path.join(cocotb_share_dir, "def")
            self._gen_import_libs(def_dir)

            for e in self.extensions:
                e.library_dirs += [def_dir]

        super().build_extensions()

    def build_extension(self, ext):
        """Build each extension in its own temp directory to make gcov happy.

        A normal PEP 517 install still works as the temp directories are discarded anyway.
        """
        ext.extra_compile_args += _extra_cxx_compile_args

        if os.name == "nt":
            # Align behavior of gcc with msvc and export only symbols marked with __declspec(dllexport)
            ext.extra_link_args += ["-Wl,--exclude-all-symbols"]
        else:
            ext.extra_link_args += ["-flto"]

            lib_name = os.path.split(ext.name)[-1]

            rpaths = []
            if lib_name == "simulator":
                rpaths += ["$ORIGIN/libs"]
                install_name = None
            else:
                rpaths += ["$ORIGIN"]
                install_name = lib_name

            if sys.platform == "darwin":
                rpaths = [rpath.replace("$ORIGIN", "@loader_path") for rpath in rpaths]
                if install_name is not None:
                    ext.extra_link_args += ["-Wl,-install_name,@rpath/%s.so" % install_name]

            ext.extra_link_args += ["-Wl,-rpath,%s" % rpath for rpath in rpaths]

        # vpi_user.h and vhpi_user.h require that WIN32 is defined
        if os.name == "nt":
            ext.define_macros += [("WIN32", "")]

        old_build_temp = self.build_temp
        self.build_temp = os.path.join(self.build_temp, ext.name)
        super().build_extension(ext)
        self.build_temp = old_build_temp

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
    elif sys.platform == "darwin":
        python_lib = os.path.join(sysconfig.get_config_var("LIBDIR"), "lib" + _get_python_lib_link() + ".")
        if os.path.exists(python_lib + "dylib"):
            python_lib += "dylib"
        else:
            python_lib += "so"
    else:
        python_lib = "lib" + _get_python_lib_link() + "." + _get_lib_ext_name()

    return python_lib


def _get_common_lib_ext(include_dir, share_lib_dir):
    """
    Defines common libraries.

    All libraries go into the same directory to enable loading without modifying the library path (e.g. LD_LIBRARY_PATH).
    In Makefile `LIB_DIR` (s) is used to point to this directory.
    """

    #
    #  libcocotbutils
    #
    libcocotbutils_sources = [
        os.path.join(share_lib_dir, "utils", "cocotb_utils.cpp")
    ]
    if os.name == "nt":
        libcocotbutils_sources += ["libcocotbutils.rc"]
    libcocotbutils_libraries = ["gpilog"]
    if os.name != "nt":
        libcocotbutils_libraries.append("dl")  # dlopen, dlerror, dlsym
    libcocotbutils = Extension(
        os.path.join("cocotb", "libs", "libcocotbutils"),
        define_macros=[("COCOTBUTILS_EXPORTS", "")] + _extra_defines,
        include_dirs=[include_dir],
        libraries=libcocotbutils_libraries,
        sources=libcocotbutils_sources,
    )

    #
    #  libgpilog
    #
    python_lib_dirs = []
    if sys.platform == "darwin":
        python_lib_dirs = [sysconfig.get_config_var("LIBDIR")]

    libgpilog_sources = [
        os.path.join(share_lib_dir, "gpi_log", "gpi_logging.cpp")
    ]
    if os.name == "nt":
        libgpilog_sources += ["libgpilog.rc"]
    libgpilog = Extension(
        os.path.join("cocotb", "libs", "libgpilog"),
        define_macros=[("GPILOG_EXPORTS", "")] + _extra_defines,
        include_dirs=[include_dir],
        sources=libgpilog_sources,
    )

    #
    #  libpygpilog
    #
    libpygpilog_sources = [
        os.path.join(share_lib_dir, "py_gpi_log", "py_gpi_logging.cpp")
    ]
    if os.name == "nt":
        libpygpilog_sources += ["libpygpilog.rc"]
    libpygpilog = Extension(
        os.path.join("cocotb", "libs", "libpygpilog"),
        define_macros=[("PYGPILOG_EXPORTS", "")] + _extra_defines,
        include_dirs=[include_dir],
        libraries=["gpilog"],
        sources=libpygpilog_sources,
    )

    #
    #  libembed
    #
    libembed_sources = [
        os.path.join(share_lib_dir, "embed", "embed.cpp")
    ]
    if os.name == "nt":
        libembed_sources += ["libembed.rc"]
    libembed = Extension(
        os.path.join("cocotb", "libs", "libembed"),
        define_macros=[
            ("COCOTB_EMBED_EXPORTS", ""),
            ("EMBED_IMPL_LIB", "libcocotb." + _get_lib_ext_name()),
            ("PYTHON_LIB", _get_python_lib())] + _extra_defines,
        include_dirs=[include_dir],
        libraries=["gpilog", "cocotbutils"],
        sources=libembed_sources,
    )

    #
    #  libcocotb
    #
    libcocotb_sources = [
        os.path.join(share_lib_dir, "embed", "gpi_embed.cpp")
    ]
    if os.name == "nt":
        libcocotb_sources += ["libcocotb.rc"]
    libcocotb = Extension(
        os.path.join("cocotb", "libs", "libcocotb"),
        define_macros=_extra_defines,
        include_dirs=[include_dir],
        libraries=["gpilog", "cocotbutils", "pygpilog"],
        sources=libcocotb_sources,
    )

    #
    #  libgpi
    #
    libgpi_sources=[
        os.path.join(share_lib_dir, "gpi", "GpiCbHdl.cpp"),
        os.path.join(share_lib_dir, "gpi", "GpiCommon.cpp"),
    ]
    if os.name == "nt":
        libgpi_sources += ["libgpi.rc"]
    libgpi = Extension(
        os.path.join("cocotb", "libs", "libgpi"),
        define_macros=[("GPI_EXPORTS", ""), ("LIB_EXT", _get_lib_ext_name()), ("SINGLETON_HANDLES", "")] + _extra_defines,
        include_dirs=[include_dir],
        libraries=["cocotbutils", "gpilog", "embed"],
        sources=libgpi_sources,
    )

    #
    #  simulator
    #
    simulator_sources=[
        os.path.join(share_lib_dir, "simulator", "simulatormodule.cpp"),
    ]
    if os.name == "nt":
        simulator_sources += ["simulator.rc"]
    libsim = Extension(
        os.path.join("cocotb", "simulator"),
        define_macros=_extra_defines,
        include_dirs=[include_dir],
        libraries=["cocotbutils", "gpilog", "gpi", "pygpilog"],
        library_dirs=python_lib_dirs,
        sources=simulator_sources,
    )

    # The libraries in this list are compiled in order of their appearance.
    # If there is a linking dependency on one library to another,
    # the linked library must be built first.
    return [libgpilog, libpygpilog, libcocotbutils, libembed, libgpi, libcocotb, libsim]


def _get_vpi_lib_ext(
    include_dir, share_lib_dir, sim_define, extra_lib=[], extra_lib_dir=[]
):
    lib_name = "libcocotbvpi_" + sim_define.lower()
    libcocotbvpi_sources = [
        os.path.join(share_lib_dir, "vpi", "VpiImpl.cpp"),
        os.path.join(share_lib_dir, "vpi", "VpiCbHdl.cpp"),
    ]
    if os.name == "nt":
        libcocotbvpi_sources += [lib_name + ".rc"]
    libcocotbvpi = Extension(
        os.path.join("cocotb", "libs", lib_name),
        define_macros=[("COCOTBVPI_EXPORTS", ""), ("VPI_CHECKING", "1")] + [(sim_define, "")] + _extra_defines,
        include_dirs=[include_dir],
        libraries=["gpi", "gpilog"] + extra_lib,
        library_dirs=extra_lib_dir,
        sources=libcocotbvpi_sources,
    )

    return libcocotbvpi


def _get_vhpi_lib_ext(
    include_dir, share_lib_dir, sim_define, extra_lib=[], extra_lib_dir=[]
):
    lib_name = "libcocotbvhpi_" + sim_define.lower()
    libcocotbvhpi_sources = [
        os.path.join(share_lib_dir, "vhpi", "VhpiImpl.cpp"),
        os.path.join(share_lib_dir, "vhpi", "VhpiCbHdl.cpp"),
    ]
    if os.name == "nt":
        libcocotbvhpi_sources += [lib_name + ".rc"]
    libcocotbvhpi = Extension(
        os.path.join("cocotb", "libs", lib_name),
        include_dirs=[include_dir],
        define_macros=[("COCOTBVHPI_EXPORTS", ""), ("VHPI_CHECKING", 1)] + [(sim_define, "")] + _extra_defines,
        libraries=["gpi", "gpilog"] + extra_lib,
        library_dirs=extra_lib_dir,
        sources=libcocotbvhpi_sources,
    )

    return libcocotbvhpi


def get_ext():

    cfg_vars = distutils.sysconfig.get_config_vars()

    if sys.platform == "darwin":
        cfg_vars["LDSHARED"] = cfg_vars["LDSHARED"].replace("-bundle", "-dynamiclib")

    share_lib_dir = os.path.relpath(os.path.join(cocotb_share_dir, "lib"))
    include_dir = os.path.relpath(os.path.join(cocotb_share_dir, "include"))

    ext = []

    logger.info("Compiling interface libraries for cocotb ...")

    ext += _get_common_lib_ext(include_dir, share_lib_dir)

    #
    #  Icarus Verilog
    #
    icarus_extra_lib = []
    logger.info("Compiling libraries for Icarus Verilog")
    if os.name == "nt":
        icarus_extra_lib = ["icarus"]

    icarus_vpi_ext = _get_vpi_lib_ext(
        include_dir=include_dir,
        share_lib_dir=share_lib_dir,
        sim_define="ICARUS",
        extra_lib=icarus_extra_lib,
    )
    ext.append(icarus_vpi_ext)

    #
    #  Modelsim/Questa
    #
    modelsim_extra_lib = []
    logger.info("Compiling libraries for Modelsim/Questa")
    if os.name == "nt":
        modelsim_extra_lib = ["modelsim"]

    modelsim_vpi_ext = _get_vpi_lib_ext(
        include_dir=include_dir,
        share_lib_dir=share_lib_dir,
        sim_define="MODELSIM",
        extra_lib=modelsim_extra_lib,
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
            fli_sources = [
                os.path.join(share_lib_dir, "fli", "FliImpl.cpp"),
                os.path.join(share_lib_dir, "fli", "FliCbHdl.cpp"),
                os.path.join(share_lib_dir, "fli", "FliObjHdl.cpp"),
            ]
            if os.name == "nt":
                fli_sources += [lib_name + ".rc"]
            fli_ext = Extension(
                os.path.join("cocotb", "libs", lib_name),
                define_macros=[("COCOTBFLI_EXPORTS", "")] + _extra_defines,
                include_dirs=[include_dir, modelsim_include_dir],
                libraries=["gpi", "gpilog"] + modelsim_extra_lib,
                sources=fli_sources,
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
    logger.info("Compiling libraries for GHDL")
    if os.name == "nt":
        ghdl_extra_lib = ["ghdl"]

    ghdl_vpi_ext = _get_vpi_lib_ext(
        include_dir=include_dir,
        share_lib_dir=share_lib_dir,
        sim_define="GHDL",
        extra_lib=ghdl_extra_lib,
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
    logger.info("Compiling libraries for Riviera")
    if os.name == "nt":
        aldec_extra_lib = ["aldec"]

    aldec_vpi_ext = _get_vpi_lib_ext(
        include_dir=include_dir,
        share_lib_dir=share_lib_dir,
        sim_define="ALDEC",
        extra_lib=aldec_extra_lib,
    )
    ext.append(aldec_vpi_ext)

    aldec_vhpi_ext = _get_vhpi_lib_ext(
        include_dir=include_dir,
        share_lib_dir=share_lib_dir,
        sim_define="ALDEC",
        extra_lib=aldec_extra_lib,
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
