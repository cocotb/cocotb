# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import distutils
import logging
import os
import subprocess
import sys
import sysconfig
import textwrap
from distutils.ccompiler import get_default_compiler
from distutils.file_util import copy_file
from typing import List

from setuptools import Extension
from setuptools.command.build_ext import build_ext as _build_ext

logger = logging.getLogger(__name__)
cocotb_share_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "src", "cocotb", "share")
)
_base_warns = [
    "-Wall",
    "-Wextra",
    "-Wcast-qual",
    "-Wwrite-strings",
    "-Wconversion",
    # -Wno-missing-field-initializers is required on GCC 4.x to prevent a
    # spurious warning `error: missing initializer for member ...` when
    # compiling `PyTypeObject type = {};` in `simulatormodule.cpp`.
    # (See https://gcc.gnu.org/bugzilla/show_bug.cgi?id=36750.) This flag can be
    # removed once we require later GCC versions.
    "-Wno-missing-field-initializers",
    "-Werror=shadow",
]
_ccx_warns = [*_base_warns, "-Wnon-virtual-dtor", "-Woverloaded-virtual"]
_extra_cxx_compile_args = [
    "-std=c++11",
    "-fvisibility=hidden",
    "-fvisibility-inlines-hidden",
    *_ccx_warns,
]
if os.name != "nt":
    _extra_cxx_compile_args += ["-flto"]

_extra_cxx_compile_args_msvc = ["/permissive-"]

# Make PRI* format macros available with C++11 compiler but older libc, e.g. on RHEL6.
_extra_defines = [("__STDC_FORMAT_MACROS", "")]


def create_sxs_assembly_manifest(
    name: str, filename: str, libraries: List[str], dependency_only=False
) -> str:
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
        dependencies.append(
            textwrap.dedent(
                """\
            <dependency>
                <dependentAssembly>
                    <assemblyIdentity name="%s" version="1.0.0.0" type="win32" processorArchitecture="%s" />
                </dependentAssembly>
            </dependency>
            """
            )
            % (lib, architecture)
        )

    if not dependency_only:
        manifest_body = textwrap.dedent(
            """\
            <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
                <assemblyIdentity name="%s" version="1.0.0.0" type="win32" processorArchitecture="%s" />
                <file name="%s" />
                %s
            </assembly>
            """
        ) % (
            name,
            architecture,
            filename,
            textwrap.indent("".join(dependencies), "    ").strip(),
        )
    else:
        manifest_body = textwrap.dedent(
            """\
            <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
                %s
            </assembly>
            """
        ) % (textwrap.indent("".join(dependencies), "    ").strip())

    return manifest_body


def create_sxs_appconfig(filename):
    """
    Create side-by-side (sxs) application configuration file.

    The application configuration specifies additional search paths for manifests.
    For more details see: https://docs.microsoft.com/en-us/windows/win32/sbscs/application-configuration-files
    """

    config_body = textwrap.dedent(
        """\
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <configuration>
            <windows>
                <assemblyBinding xmlns="urn:schemas-microsoft-com:asm.v1">
                    <probing privatePath="libs" />
                </assemblyBinding>
            </windows>
        </configuration>
        """
    )

    dirpath = os.path.dirname(filename)
    os.makedirs(dirpath, exist_ok=True)

    with open(filename + ".2.config", "w", encoding="utf-8") as f:
        f.write(config_body)


def create_rc_file(rc_filename, name, filename, libraries, runtime_libraries):
    """
    Creates windows resource definition script to embed the side-by-side assembly manifest into the libraries.

    For more details see: https://docs.microsoft.com/en-us/windows/win32/menurc/about-resource-files
    """

    manifest = create_sxs_assembly_manifest(name, filename, libraries)

    # Escape double quotes and put every line between double quotes for embedding into rc file
    manifest = manifest.replace('"', '""')
    manifest = "\n".join([f'"{x}\\r\\n"' for x in manifest.splitlines()])

    rc_body = (
        textwrap.dedent(
            """\
        #pragma code_page(65001) // UTF-8
        #include <Windows.h>

        LANGUAGE 0x00, 0x00

        ISOLATIONAWARE_MANIFEST_RESOURCE_ID RT_MANIFEST
        BEGIN
        %s
        END
        """
        )
        % manifest
    )

    if runtime_libraries is not None:
        manifest = create_sxs_assembly_manifest(
            name, filename, runtime_libraries, dependency_only=True
        )

        # Escape double quotes and put every line between double quotes for embedding into rc file
        manifest = manifest.replace('"', '""')
        manifest = "\n".join([f'"{x}\\r\\n"' for x in manifest.splitlines()])

        rc_body += (
            textwrap.dedent(
                """\
            1000 RT_MANIFEST
            BEGIN
            %s
            END
            """
            )
            % manifest
        )

    with open(rc_filename, "w", encoding="utf-8") as f:
        f.write(rc_body)


def _get_lib_ext_name():
    """Get name of default library file extension on given OS."""

    if os.name == "nt":
        ext_name = "dll"
    else:
        ext_name = "so"

    return ext_name


class build_ext(_build_ext):
    def _uses_msvc(self):
        if self.compiler == "msvc":
            return True
        if self.compiler is None:
            return get_default_compiler() == "msvc"
        else:
            return getattr(self.compiler, "compiler_type", None) == "msvc"

    def run(self):
        if os.name == "nt":
            create_sxs_appconfig(
                self.get_ext_fullpath(os.path.join("cocotb", "simulator"))
            )

        super().run()

    def build_extensions(self):
        if os.name == "nt":
            if self._uses_msvc():
                # Initialize the compiler now so that compiler/linker flags are populated
                if not self.compiler.initialized:
                    self.compiler.initialize()

                # Setuptools defaults to activate automatic manifest generation for msvc,
                # disable it here as we manually generate it to also support mingw on windows
                for k, ldflags in self.compiler._ldflags.items():
                    self.compiler._ldflags[k] = [
                        x for x in ldflags if not x.startswith("/MANIFEST")
                    ] + ["/MANIFEST:NO"]

                self.compiler.compile_options = [
                    x for x in self.compiler.compile_options if not x.startswith("/W")
                ] + ["/W4"]

            ext_names = {os.path.split(ext.name)[-1] for ext in self.extensions}
            for ext in self.extensions:
                fullname = self.get_ext_fullname(ext.name)
                filename = self.get_ext_filename(fullname)
                name = os.path.split(fullname)[-1]
                filename = os.path.split(filename)[-1]
                libraries = {"lib" + lib for lib in ext.libraries}.intersection(
                    ext_names
                )
                rc_filename = name + ".rc"
                runtime_libraries = None

                # Add the runtime dependency on libcocotb to libembed
                if name == "libembed":
                    runtime_libraries = ["libcocotb"]

                # Strip lib prefix for msvc
                if self._uses_msvc():
                    name = name[3:] if name.startswith("lib") else name
                    libraries = {
                        (lib[3:] if lib.startswith("lib") else lib) for lib in libraries
                    }
                    if runtime_libraries is not None:
                        runtime_libraries = {
                            (lib[3:] if lib.startswith("lib") else lib)
                            for lib in runtime_libraries
                        }
                create_rc_file(
                    rc_filename, name, filename, libraries, runtime_libraries
                )

            def_dir = os.path.join(cocotb_share_dir, "def")
            self._gen_import_libs(def_dir)

            for e in self.extensions:
                e.library_dirs += [def_dir]

        super().build_extensions()

    def build_extension(self, ext):
        """Build each extension in its own temp directory to make gcov happy.

        A normal PEP 517 install still works as the temp directories are discarded anyway.
        """
        lib_name = os.path.split(ext.name)[-1]

        if self._uses_msvc():
            ext.extra_compile_args += _extra_cxx_compile_args_msvc
        else:
            ext.extra_compile_args += _extra_cxx_compile_args

            if os.name == "nt":
                # Align behavior of gcc with msvc and export only symbols marked with __declspec(dllexport)
                ext.extra_link_args += ["-Wl,--exclude-all-symbols"]
            else:
                ext.extra_link_args += ["-flto"]

                rpaths = []
                if lib_name == "simulator":
                    rpaths += ["$ORIGIN/libs"]
                    install_name = None
                else:
                    rpaths += ["$ORIGIN"]
                    install_name = lib_name

                if sys.platform == "darwin":
                    rpaths = [
                        rpath.replace("$ORIGIN", "@loader_path") for rpath in rpaths
                    ]
                    if install_name is not None:
                        ext.extra_link_args += [
                            f"-Wl,-install_name,@rpath/{install_name}.so"
                        ]

                if sys.platform == "linux":
                    # Avoid a runtime dependency on libstdc++. Some simulators
                    # ship a version of libstdc++6.so which is older than the
                    # one cocotb has been compiled with, which will then lead to
                    # load-time errors like "libstdc++.so.6: version
                    # `GLIBCXX_3.4.29' not found (required by
                    # /path/to/libcocotbvhpi_modelsim.so)."
                    ext.extra_link_args += ["-static-libstdc++"]

                ext.extra_link_args += [f"-Wl,-rpath,{rpath}" for rpath in rpaths]

        # vpi_user.h and vhpi_user.h require that WIN32 is defined
        if os.name == "nt":
            ext.define_macros += [("WIN32", "")]

        if lib_name == "libembed":
            if self._uses_msvc():
                embed_lib_name = "cocotb"
            else:
                embed_lib_name = "libcocotb"
            ext.define_macros += [
                ("EMBED_IMPL_LIB", embed_lib_name + "." + _get_lib_ext_name())
            ]

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
        if os.path.split(ext_name)[-1] == "simulator":
            return filename

        head, tail = os.path.split(filename)
        tail_split = tail.split(".")

        # mingw on msys2 uses `-` as separator
        tail_split = tail_split[0].split("-")

        # strip lib prefix if msvc is used
        if self._uses_msvc() and tail_split[0].startswith("lib"):
            tail_split[0] = tail_split[0][3:]

        filename_short = os.path.join(head, tail_split[0] + "." + _get_lib_ext_name())

        # icarus requires vpl extension
        filename_short = filename_short.replace(
            "libcocotbvpi_icarus.so", "libcocotbvpi_icarus.vpl"
        )
        filename_short = filename_short.replace(
            "libcocotbvpi_icarus.dll", "libcocotbvpi_icarus.vpl"
        )
        filename_short = filename_short.replace(
            "cocotbvpi_icarus.dll", "cocotbvpi_icarus.vpl"
        )

        return filename_short

    def finalize_options(self):
        """Like the base class method,but add extra library_dirs path."""

        super().finalize_options()

        for ext in self.extensions:
            ext.library_dirs.append(os.path.join(self.build_lib, "cocotb", "libs"))

    def copy_extensions_to_source(self):
        """Like the base class method, but copy libs into proper directory in develop."""

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
            if self._uses_msvc():
                subprocess.run(
                    [
                        self.compiler.lib,
                        "/def:" + os.path.join(def_dir, sim + ".def"),
                        "/out:" + os.path.join(def_dir, sim + ".lib"),
                        "/machine:" + ("X64" if sys.maxsize > 2**32 else "X86"),
                    ],
                    check=True,
                )
            else:
                subprocess.run(
                    [
                        "dlltool",
                        "-d",
                        os.path.join(def_dir, sim + ".def"),
                        "-l",
                        os.path.join(def_dir, "lib" + sim + ".a"),
                    ],
                    check=True,
                )


def _get_python_lib_link():
    """Get name of python library used for linking"""

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
    """Get the library for embedded the python interpreter"""

    if os.name == "nt":
        python_lib = _get_python_lib_link() + "." + _get_lib_ext_name()
    elif sys.platform == "darwin":
        python_lib = os.path.join(
            sysconfig.get_config_var("LIBDIR"), "lib" + _get_python_lib_link() + "."
        )
        if os.path.exists(python_lib + "dylib"):
            python_lib += "dylib"
        else:
            python_lib += "so"
    else:
        python_lib = "lib" + _get_python_lib_link() + "." + _get_lib_ext_name()

    return python_lib


def _get_common_lib_ext(include_dirs, share_lib_dir):
    """
    Defines common libraries.

    All libraries go into the same directory to enable loading without modifying the library path (e.g. LD_LIBRARY_PATH).
    """

    #
    #  libcocotbutils
    #
    libcocotbutils_sources = [os.path.join(share_lib_dir, "utils", "cocotb_utils.cpp")]
    if os.name == "nt":
        libcocotbutils_sources += ["libcocotbutils.rc"]
    libcocotbutils_libraries = ["gpilog"]
    if sys.platform.startswith(("linux", "darwin", "cygwin", "msys")):
        libcocotbutils_libraries.append("dl")  # dlopen, dlerror, dlsym
    libcocotbutils = Extension(
        os.path.join("cocotb", "libs", "libcocotbutils"),
        define_macros=[("COCOTBUTILS_EXPORTS", ""), *_extra_defines],
        include_dirs=include_dirs,
        libraries=libcocotbutils_libraries,
        sources=libcocotbutils_sources,
    )

    #
    #  libgpilog
    #
    python_lib_dirs = []
    if sys.platform == "darwin":
        python_lib_dirs = [sysconfig.get_config_var("LIBDIR")]

    libgpilog_sources = [os.path.join(share_lib_dir, "gpi_log", "gpi_logging.cpp")]
    if os.name == "nt":
        libgpilog_sources += ["libgpilog.rc"]
    libgpilog = Extension(
        os.path.join("cocotb", "libs", "libgpilog"),
        define_macros=[("GPILOG_EXPORTS", ""), *_extra_defines],
        include_dirs=include_dirs,
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
        define_macros=[("PYGPILOG_EXPORTS", ""), *_extra_defines],
        include_dirs=include_dirs,
        libraries=["gpilog"],
        sources=libpygpilog_sources,
    )

    #
    #  libembed
    #
    libembed_sources = [os.path.join(share_lib_dir, "embed", "embed.cpp")]
    if os.name == "nt":
        libembed_sources += ["libembed.rc"]
    libembed = Extension(
        os.path.join("cocotb", "libs", "libembed"),
        define_macros=[
            ("COCOTB_EMBED_EXPORTS", ""),
            ("PYTHON_LIB", _get_python_lib()),
            *_extra_defines,
        ],
        include_dirs=include_dirs,
        libraries=["gpilog", "cocotbutils"],
        sources=libembed_sources,
    )

    #
    #  libcocotb
    #
    libcocotb_sources = [os.path.join(share_lib_dir, "embed", "gpi_embed.cpp")]
    if os.name == "nt":
        libcocotb_sources += ["libcocotb.rc"]
    libcocotb = Extension(
        os.path.join("cocotb", "libs", "libcocotb"),
        define_macros=_extra_defines,
        include_dirs=include_dirs,
        libraries=["gpilog", "cocotbutils", "pygpilog", "gpi"],
        sources=libcocotb_sources,
    )

    #
    #  libgpi
    #
    libgpi_sources = [
        os.path.join(share_lib_dir, "gpi", "GpiCbHdl.cpp"),
        os.path.join(share_lib_dir, "gpi", "GpiCommon.cpp"),
    ]
    if os.name == "nt":
        libgpi_sources += ["libgpi.rc"]
    libgpi = Extension(
        os.path.join("cocotb", "libs", "libgpi"),
        define_macros=[
            ("GPI_EXPORTS", ""),
            ("LIB_EXT", _get_lib_ext_name()),
            ("SINGLETON_HANDLES", ""),
            *_extra_defines,
        ],
        include_dirs=include_dirs,
        libraries=["cocotbutils", "gpilog", "embed"],
        sources=libgpi_sources,
    )

    #
    #  simulator
    #
    simulator_sources = [
        os.path.join(share_lib_dir, "simulator", "simulatormodule.cpp"),
    ]
    if os.name == "nt":
        simulator_sources += ["simulator.rc"]
    libsim = Extension(
        os.path.join("cocotb", "simulator"),
        define_macros=_extra_defines,
        include_dirs=include_dirs,
        libraries=["cocotbutils", "gpilog", "gpi", "pygpilog"],
        library_dirs=python_lib_dirs,
        sources=simulator_sources,
    )

    # The libraries in this list are compiled in order of their appearance.
    # If there is a linking dependency on one library to another,
    # the linked library must be built first.
    return [libgpilog, libpygpilog, libcocotbutils, libembed, libgpi, libcocotb, libsim]


def _get_vpi_lib_ext(
    include_dirs, share_lib_dir, sim_define, extra_lib=[], extra_lib_dir=[]
):
    lib_name = "libcocotbvpi_" + sim_define.lower()
    libcocotbvpi_sources = [
        os.path.join(share_lib_dir, "vpi", "VpiImpl.cpp"),
        os.path.join(share_lib_dir, "vpi", "VpiCbHdl.cpp"),
        os.path.join(share_lib_dir, "vpi", "VpiObj.cpp"),
        os.path.join(share_lib_dir, "vpi", "VpiIterator.cpp"),
        os.path.join(share_lib_dir, "vpi", "VpiSignal.cpp"),
    ]
    if os.name == "nt":
        libcocotbvpi_sources += [lib_name + ".rc"]
    libcocotbvpi = Extension(
        os.path.join("cocotb", "libs", lib_name),
        define_macros=[("COCOTBVPI_EXPORTS", ""), (sim_define, ""), *_extra_defines],
        include_dirs=include_dirs,
        libraries=["gpi", "gpilog", *extra_lib],
        library_dirs=extra_lib_dir,
        sources=libcocotbvpi_sources,
    )

    return libcocotbvpi


def _get_vhpi_lib_ext(
    include_dirs, share_lib_dir, sim_define, extra_lib=[], extra_lib_dir=[]
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
        include_dirs=include_dirs,
        define_macros=[("COCOTBVHPI_EXPORTS", ""), (sim_define, ""), *_extra_defines],
        libraries=["gpi", "gpilog", *extra_lib],
        library_dirs=extra_lib_dir,
        sources=libcocotbvhpi_sources,
    )

    return libcocotbvhpi


def get_ext():
    cfg_vars = distutils.sysconfig.get_config_vars()

    if sys.platform == "darwin":
        cfg_vars["LDSHARED"] = cfg_vars["LDSHARED"].replace("-bundle", "-dynamiclib")
        cfg_vars["LDCXXSHARED"] = cfg_vars["LDSHARED"].replace("-bundle", "-dynamiclib")

    share_lib_dir = os.path.relpath(os.path.join(cocotb_share_dir, "lib"))
    include_dirs = [
        os.path.relpath(os.path.join(cocotb_share_dir, "include")),
        os.path.relpath(os.path.join(os.path.dirname(__file__), "src", "cocotb")),
    ]

    ext = []

    logger.info("Compiling interface libraries for cocotb ...")

    ext += _get_common_lib_ext(include_dirs, share_lib_dir)

    #
    #  Icarus Verilog
    #
    icarus_extra_lib = []
    logger.info("Compiling libraries for Icarus Verilog")
    if os.name == "nt":
        icarus_extra_lib = ["icarus"]

    icarus_vpi_ext = _get_vpi_lib_ext(
        include_dirs=include_dirs,
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
        include_dirs=include_dirs,
        share_lib_dir=share_lib_dir,
        sim_define="MODELSIM",
        extra_lib=modelsim_extra_lib,
    )
    ext.append(modelsim_vpi_ext)

    modelsim_vhpi_ext = _get_vhpi_lib_ext(
        include_dirs=include_dirs,
        share_lib_dir=share_lib_dir,
        sim_define="MODELSIM",
        extra_lib=modelsim_extra_lib,
    )
    ext.append(modelsim_vhpi_ext)

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
        define_macros=[("COCOTBFLI_EXPORTS", ""), *_extra_defines],
        include_dirs=include_dirs,
        libraries=["gpi", "gpilog", *modelsim_extra_lib],
        sources=fli_sources,
    )

    ext.append(fli_ext)

    #
    # GHDL
    #
    ghdl_extra_lib = []
    logger.info("Compiling libraries for GHDL")
    if os.name == "nt":
        ghdl_extra_lib = ["ghdl"]

    ghdl_vpi_ext = _get_vpi_lib_ext(
        include_dirs=include_dirs,
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
            include_dirs=include_dirs, share_lib_dir=share_lib_dir, sim_define="IUS"
        )
        ext.append(ius_vpi_ext)

        ius_vhpi_ext = _get_vhpi_lib_ext(
            include_dirs=include_dirs, share_lib_dir=share_lib_dir, sim_define="IUS"
        )
        ext.append(ius_vhpi_ext)

    #
    # VCS
    #
    if os.name == "posix":
        logger.info("Compiling libraries for VCS")
        vcs_vpi_ext = _get_vpi_lib_ext(
            include_dirs=include_dirs, share_lib_dir=share_lib_dir, sim_define="VCS"
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
        include_dirs=include_dirs,
        share_lib_dir=share_lib_dir,
        sim_define="ALDEC",
        extra_lib=aldec_extra_lib,
    )
    ext.append(aldec_vpi_ext)

    aldec_vhpi_ext = _get_vhpi_lib_ext(
        include_dirs=include_dirs,
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
            include_dirs=include_dirs,
            share_lib_dir=share_lib_dir,
            sim_define="VERILATOR",
        )
        ext.append(verilator_vpi_ext)

    #
    # NVC
    #
    if os.name == "posix":
        logger.info("Compiling libraries for NVC")
        nvc_vhpi_ext = _get_vhpi_lib_ext(
            include_dirs=include_dirs, share_lib_dir=share_lib_dir, sim_define="NVC"
        )
        ext.append(nvc_vhpi_ext)

    #
    # DSim
    #
    if os.name == "posix":
        logger.info("Compiling libraries for DSim")
        dsim_vpi_ext = _get_vpi_lib_ext(
            include_dirs=include_dirs, share_lib_dir=share_lib_dir, sim_define="DSim"
        )
        ext.append(dsim_vpi_ext)

    return ext
