"""A run class."""

from subprocess import Popen
import os
import sys
import sysconfig
import cocotb
import errno
import distutils

from setuptools import Extension
from setuptools.command.build_ext import build_ext
from setuptools.dist import Distribution

cfg_vars = distutils.sysconfig.get_config_vars()
for key, value in cfg_vars.items():
    if type(value) == str:
        cfg_vars[key] = value.replace("-Wstrict-prototypes", "")


def _symlink_force(target, link_name):
    try:
        os.symlink(target, link_name)
    except OSError as e:
        if e.errno == errno.EEXIST:
            os.remove(link_name)
            os.symlink(target, link_name)
        else:
            raise e


def _build_lib(lib, dist):
    dist.ext_modules = [lib]
    _build_ext = build_ext(dist)
    _build_ext.finalize_options()

    _build_ext.run()
    out_lib = _build_ext.get_outputs()

    lib_name = lib.name
    lib_path = os.path.abspath(out_lib[0])
    dir_name = os.path.dirname(lib_path)
    ext_name = os.path.splitext(lib_path)[1][1:]

    print("Building:", out_lib[0])

    _symlink_force(
        lib_path, os.path.join(os.path.abspath(dir_name), lib_name + "." + ext_name)
    )

    return dir_name


def build_libs():
    share_dir = os.path.join(os.path.dirname(cocotb.__file__), "share")

    python_lib = sysconfig.get_config_var("LDLIBRARY")
    python_lib_link = os.path.splitext(python_lib)[0][3:]

    dist = Distribution()
    dist.parse_config_files()

    libcocotbutils = Extension(
        "libcocotbutils",
        include_dirs=[share_dir + "/include"],
        sources=[share_dir + "/lib/utils/cocotb_utils.c"],
    )

    lib_path = _build_lib(libcocotbutils, dist)

    libgpilog = Extension(
        "libgpilog",
        include_dirs=[share_dir + "/include"],
        libraries=[python_lib_link, "pthread", "dl", "util", "rt", "m", "cocotbutils"],
        library_dirs=[lib_path],
        sources=[share_dir + "/lib/gpi_log/gpi_logging.c"],
    )

    _build_lib(libgpilog, dist)

    libcocotb = Extension(
        "libcocotb",
        define_macros=[("PYTHON_SO_LIB", python_lib)],
        include_dirs=[share_dir + "/include"],
        sources=[share_dir + "/lib/embed/gpi_embed.c"],
    )

    _build_lib(libcocotb, dist)

    libgpi = Extension(
        "libgpi",
        include_dirs=[share_dir + "/include"],
        libraries=["cocotbutils", "gpilog", "cocotb", "stdc++"],
        library_dirs=[lib_path],
        sources=[
            share_dir + "/lib/gpi/GpiCbHdl.cpp",
            share_dir + "/lib/gpi/GpiCommon.cpp",
        ],
    )

    _build_lib(libgpi, dist)

    libsim = Extension(
        "libsim",
        include_dirs=[share_dir + "/include"],
        sources=[share_dir + "/lib/simulator/simulatormodule.c"],
    )

    _build_lib(libsim, dist)

    libvpi = Extension(
        "libvpi",
        include_dirs=[share_dir + "/include"],
        libraries=["gpi", "gpilog"],
        library_dirs=[lib_path],
        sources=[
            share_dir + "/lib/vpi/VpiImpl.cpp",
            share_dir + "/lib/vpi/VpiCbHdl.cpp",
        ],
    )

    _build_lib(libvpi, dist)

    _symlink_force(
        os.path.join(os.path.abspath(lib_path), "libvpi.so"),
        os.path.join(os.path.abspath(lib_path), "gpivpi.vpl"),
    )
    _symlink_force(
        os.path.join(os.path.abspath(lib_path), "libvpi.so"),
        os.path.join(os.path.abspath(lib_path), "cocotb.vpl"),
    )
    _symlink_force(
        os.path.join(os.path.abspath(lib_path), "libsim.so"),
        os.path.join(os.path.abspath(lib_path), "simulator.so"),
    )

    return lib_path


def Run(sources, toplevel, module):

    libs_dir = build_libs()

    my_env = os.environ
    my_env["LD_LIBRARY_PATH"] = libs_dir + ":" + sysconfig.get_config_var("LIBDIR")

    python_path = ":".join(sys.path)
    my_env["PYTHONPATH"] = python_path + ":" + libs_dir
    my_env["TOPLEVEL"] = toplevel
    my_env["TOPLEVEL_LANG"] = "verilog"
    my_env["COCOTB_SIM"] = "1"
    my_env["MODULE"] = module

    os.makedirs("sim_build", exist_ok=True)

    sources_abs = []
    for src in sources:
        sources_abs.append(os.path.abspath(src))

    comp_cmd = [
        "iverilog",
        "-o",
        "sim_build/sim.vvp",
        "-D",
        "COCOTB_SIM=1",
        "-s",
        toplevel,
        "-g2012",
    ] + sources_abs
    print(" ".join(comp_cmd))
    process = Popen(comp_cmd).wait()

    cmd = ["vvp", "-M", libs_dir, "-m", "gpivpi", "sim_build/sim.vvp"]
    print(" ".join(cmd))
    process = Popen(cmd).wait()
