# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause


import subprocess
import os
import sys
import tempfile
import re
import shutil
import warnings
from xml.etree import cElementTree as ET
import threading
import signal
import cocotb.config
import sysconfig
from distutils.spawn import find_executable

warnings.warn(
    "Python runners and associated APIs are an experimental feature and subject to change.", UserWarning, stacklevel=2
)

_magic_re = re.compile(r"([\\{}])")
_space_re = re.compile(r"([\s])", re.ASCII)


def as_tcl_value(value):
    # add '\' before special characters and spaces
    value = _magic_re.sub(r"\\\1", value)
    value = value.replace("\n", r"\n")
    value = _space_re.sub(r"\\\1", value)
    if value[0] == '"':
        value = "\\" + value

    return value


class Simulator(object):
    def __init__(self):

        self.check_simulator()

        self.env = {}

        # Catch SIGINT and SIGTERM
        self.old_sigint_h = signal.getsignal(signal.SIGINT)
        self.old_sigterm_h = signal.getsignal(signal.SIGTERM)

        # works only if main thread
        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGINT, self.exit_gracefully)
            signal.signal(signal.SIGTERM, self.exit_gracefully)

        self.process = None

    @staticmethod
    def check_simulator():
        raise NotImplementedError()

    def init_dir(self, build_dir, work_dir):

        if build_dir is not None:
            self.build_dir = os.path.abspath(build_dir)

        self.work_dir = self.build_dir

        if work_dir is not None:
            absworkdir = os.path.abspath(work_dir)
            if os.path.isdir(absworkdir):
                self.work_dir = absworkdir

    def set_env(self):

        for e in os.environ:
            self.env[e] = os.environ[e]

        if "LIBPYTHON_LOC" not in self.env:
            self.env["LIBPYTHON_LOC"] = cocotb._vendor.find_libpython.find_libpython()

        self.env["PATH"] += os.pathsep + cocotb.config.libs_dir

        self.env["PYTHONPATH"] = os.pathsep.join(sys.path)
        for path in self.python_search:
            self.env["PYTHONPATH"] += os.pathsep + path

        self.env["PYTHONHOME"] = sysconfig.get_config_var("prefix")

        self.env["TOPLEVEL"] = self.hdl_topmodule
        self.env["MODULE"] = self.module

        if not os.path.exists(self.build_dir):
            os.makedirs(self.build_dir)

    def build_command(self):
        raise NotImplementedError()

    def test_command(self):
        raise NotImplementedError()

    def build(
        self,
        library_name="work",
        verilog_sources=[],
        vhdl_sources=[],
        includes=[],
        defines=[],
        parameters={},
        extra_args=[],
        hdl_topmodule=None,
        always=False,
        build_dir="sim_build",
        work_dir=None,
    ):
        self.init_dir(build_dir, work_dir)
        os.makedirs(self.build_dir, exist_ok=True)

        # note: to avoid mutating argument defaults, we ensure that no value
        # is written without a copy. This is much more concise and leads to
        # a better docstring than using `None` as a default in the parameters
        # list.
        self.library_name = library_name
        self.verilog_sources = self.get_abs_paths(verilog_sources)
        self.vhdl_sources = self.get_abs_paths(vhdl_sources)
        self.includes = self.get_abs_paths(includes)
        self.defines = list(defines)
        self.parameters = dict(parameters)
        self.compile_args = extra_args
        self.always = always
        self.hdl_topmodule = hdl_topmodule

        for e in os.environ:
            self.env[e] = os.environ[e]

        cmds = self.build_command()
        self.execute(cmds)

    def test(
        self,
        py_module,
        hdl_topmodule,
        toplevel_lang="verilog",
        testcase=None,
        seed=None,
        python_search=[],
        extra_args=[],
        plus_args=[],
        extra_env=None,
        waves=None,
        gui=None,
        build_dir=None,
        work_dir=None,
    ):

        self.init_dir(build_dir, work_dir)

        if isinstance(py_module, str):
            self.module = py_module
        else:
            self.module = ",".join(py_module)

        # note: to avoid mutating argument defaults, we ensure that no value
        # is written without a copy. This is much more concise and leads to
        # a better docstring than using `None` as a default in the parameters
        # list.
        self.python_search = list(python_search)
        self.hdl_topmodule = hdl_topmodule
        self.toplevel_lang = toplevel_lang
        self.sim_args = extra_args
        self.plus_args = list(plus_args)
        self.env = dict(extra_env) if extra_env is not None else {}

        if testcase is not None:
            self.env["TESTCASE"] = testcase

        if seed is not None:
            self.env["RANDOM_SEED"] = str(seed)

        if waves is None:
            self.waves = bool(int(os.getenv("WAVES", 0)))
        else:
            self.waves = bool(waves)

        if gui is None:
            self.gui = bool(int(os.getenv("GUI", 0)))
        else:
            self.gui = bool(gui)

        results_xml_file = os.getenv("COCOTB_RESULTS_FILE", os.path.join(self.build_dir, "results.xml"))

        try:
            os.remove(results_xml_file)
        except OSError:
            pass

        cmds = self.test_command()
        self.set_env()
        self.execute(cmds)

        self.check_results_file(results_xml_file)

        print("INFO: Results file: %s" % results_xml_file)
        return results_xml_file

    @staticmethod
    def check_results_file(results_xml_file):

        __tracebackhide__ = True  # Hide the traceback when using PyTest.

        results_file_exist = os.path.isfile(results_xml_file)
        if not results_file_exist:
            raise SystemExit("ERROR: Simulation terminated abnormally. Results file not found.")

        failed = 0

        tree = ET.parse(results_xml_file)
        for ts in tree.iter("testsuite"):
            for tc in ts.iter("testcase"):
                for _ in tc.iter("failure"):
                    failed += 1

        if failed:
            raise SystemExit("ERROR: Failed %d tests." % failed)

    @staticmethod
    def get_include_commands(includes):
        raise NotImplementedError()

    @staticmethod
    def get_define_commands(defines):
        raise NotImplementedError()

    def get_parameter_commands(self, parameters):
        raise NotImplementedError()

    @staticmethod
    def get_abs_paths(paths):
        paths_abs = []
        for path in paths:
            if os.path.isabs(path):
                paths_abs.append(os.path.abspath(path))
            else:
                paths_abs.append(os.path.abspath(os.path.join(os.getcwd(), path)))

        return paths_abs

    def execute(self, cmds):

        __tracebackhide__ = True  # Hide the traceback when using PyTest.

        for cmd in cmds:
            print("INFO: Running command: " + ' "'.join(cmd) + '" in directory:"' + self.work_dir + '"')

            # TODO: create at thread to handle stderr and log as error?
            # TODO: log forwarding

            self.process = subprocess.run(cmd, cwd=self.work_dir, env=self.env)

            if self.process.returncode != 0:
                raise SystemExit(
                    "Process '%s' termindated with error %d" % (self.process.args[0], self.process.returncode)
                )

            self.process = None

    @staticmethod
    def outdated(output, dependencies):

        if not os.path.isfile(output):
            return True

        output_mtime = os.path.getmtime(output)

        dep_mtime = 0
        for file in dependencies:
            mtime = os.path.getmtime(file)
            if mtime > dep_mtime:
                dep_mtime = mtime

        if dep_mtime > output_mtime:
            return True

        return False

    def exit_gracefully(self, signum, frame):
        pid = None
        if self.process is not None:
            pid = self.process.pid
            self.process.stdout.flush()
            self.process.kill()
            self.process.wait()
        # Restore previous handlers
        signal.signal(signal.SIGINT, self.old_sigint_h)
        signal.signal(signal.SIGTERM, self.old_sigterm_h)
        raise SystemExit("Exiting pid: {} with signum: {}".format(str(pid), str(signum)))


class Icarus(Simulator):
    def __init__(self, *argv, **kwargs):
        super().__init__(*argv, **kwargs)

    @staticmethod
    def check_simulator():
        if find_executable("iverilog") is None:
            raise SystemExit("ERROR: iverilog exacutable not found!")

    @staticmethod
    def get_include_commands(includes):
        return ["-I" + dir for dir in includes]

    @staticmethod
    def get_define_commands(defines):
        return ["-D" + define for define in defines]

    def get_parameter_commands(self, parameters):
        return [
            "-P" + self.hdl_topmodule + "." + name + "=" + str(value) for name, value in parameters.items()
        ]

    def test_command(self):

        return [
            [
                "vvp",
                "-M",
                cocotb.config.libs_dir,
                "-m",
                cocotb.config.lib_name("vpi", "icarus"),
            ]
            + self.sim_args
            + [self.sim_file]
            + self.plus_args
        ]

    def build_command(self):

        if self.vhdl_sources:
            raise ValueError("This simulator does not support VHDL")

        self.sim_file = os.path.join(self.build_dir, self.library_name + ".vvp")

        cmd = []
        if self.outdated(self.sim_file, self.verilog_sources) or self.always:

            cmd = [
                ["iverilog", "-o", self.sim_file, "-D", "COCOTB_SIM=1", "-g2012"]
                + self.get_define_commands(self.defines)
                + self.get_include_commands(self.includes)
                + self.get_parameter_commands(self.parameters)
                + self.compile_args
                + self.verilog_sources
            ]

        else:
            print("WARNING: Skipping compilation:" + self.sim_file)

        return cmd


class Questa(Simulator):
    @staticmethod
    def check_simulator():
        if find_executable("vsim") is None:
            raise SystemExit("ERROR: vsim exacutable not found!")

    @staticmethod
    def get_include_commands(includes):
        return ["+incdir+" + as_tcl_value(dir) for dir in includes]

    @staticmethod
    def get_define_commands(defines):
        return ["+define+" + as_tcl_value(define) for define in defines]

    def get_parameter_commands(self, parameters):
        return ["-g" + name + "=" + str(value) for name, value in parameters.items()]

    def build_command(self):

        cmd = []

        if self.vhdl_sources:
            cmd.append(["vlib", as_tcl_value(self.library_name)])
            cmd.append(
                ["vcom", "-mixedsvvh"]
                + ["-work", as_tcl_value(self.library_name)]
                + [as_tcl_value(v) for v in self.compile_args]
                + [as_tcl_value(v) for v in self.vhdl_sources]
            )

        if self.verilog_sources:
            cmd.append(["vlib", as_tcl_value(self.library_name)])
            cmd.append(
                ["vlog", "-mixedsvvh"]
                + ([] if self.always else ["-incr"])
                + ["-work", as_tcl_value(self.library_name)]
                + ["+define+COCOTB_SIM"]
                + ["-sv"]
                + self.get_define_commands(self.defines)
                + self.get_include_commands(self.includes)
                + [as_tcl_value(v) for v in self.compile_args]
                + [as_tcl_value(v) for v in self.verilog_sources]
            )

        return cmd

    def test_command(self):

        cmd = []

        do_script = ""
        if self.waves:
            do_script += "log -recursive /*;"

        if not self.gui:
            do_script += "run -all; quit"

        if self.toplevel_lang == "vhdl":
            cmd.append(
                ["vsim"]
                + ["-gui" if self.gui else "-c"]
                + ["-onfinish", "stop" if self.gui else "exit"]
                + ["-foreign", "cocotb_init " + as_tcl_value(cocotb.config.lib_name_path("fli", "questa"))]
                + [as_tcl_value(v) for v in self.sim_args]
                + [as_tcl_value(v) for v in self.get_parameter_commands(self.parameters)]
                + [as_tcl_value(self.hdl_topmodule)]
                + ["-do", do_script]
            )

            if self.verilog_sources:
                self.env["GPI_EXTRA"] = cocotb.config.lib_name_path("vpi", "questa") + ":cocotbvpi_entry_point"

        else:
            cmd.append(
                ["vsim"]
                + ["-gui" if self.gui else "-c"]
                + ["-onfinish", "stop" if self.gui else "exit"]
                + ["-pli", as_tcl_value(cocotb.config.lib_name_path("vpi", "questa"))]
                + [as_tcl_value(v) for v in self.sim_args]
                + [as_tcl_value(v) for v in self.get_parameter_commands(self.parameters)]
                + [as_tcl_value(self.hdl_topmodule)]
                + [as_tcl_value(v) for v in self.plus_args]
                + ["-do", do_script]
            )

            if self.vhdl_sources:
                self.env["GPI_EXTRA"] = cocotb.config.lib_name_path("fli", "questa") + ":cocotbfli_entry_point"

        return cmd


class Ghdl(Simulator):
    @staticmethod
    def check_simulator():
        if find_executable("ghdl") is None:
            raise SystemExit("ERROR: ghdl exacutable not found!")

    @staticmethod
    def get_include_commands(includes):
        include_cmd = []
        for dir in includes:
            include_cmd.append("-I")
            include_cmd.append(dir)

        return include_cmd

    @staticmethod
    def get_define_commands(defines):
        defines_cmd = []
        for define in defines:
            defines_cmd.append("-D")
            defines_cmd.append(define)

    def get_parameter_commands(self, parameters):
        return ["-g" + name + "=" + str(value) for name, value in parameters.items()]

    def build_command(self):

        if self.verilog_sources:
            raise ValueError("This simulator does not support Verilog")

        return [
            ["ghdl", "-i"] + ["--work=%s" % self.library_name] + self.compile_args + [source_file]
            for source_file in self.vhdl_sources
        ]

    def test_command(self):

        cmd_elaborate = ["ghdl", "-m"] + ["--work=%s" % self.library_name] + self.compile_args + [self.hdl_topmodule]

        cmd = [cmd_elaborate]
        cmd_run = (
            ["ghdl", "-r"]
            + self.compile_args
            + [self.hdl_topmodule]
            + ["--vpi=" + cocotb.config.lib_name_path("vpi", "ghdl")]
            + self.sim_args
            + self.get_parameter_commands(self.parameters)
        )

        cmd.append(cmd_run)

        return cmd


class Riviera(Simulator):
    @staticmethod
    def check_simulator():
        if find_executable("vsimsa") is None:
            raise SystemExit("ERROR: vsimsa exacutable not found!")

    @staticmethod
    def get_include_commands(includes):
        return ["+incdir+" + as_tcl_value(dir) for dir in includes]

    @staticmethod
    def get_define_commands(defines):
        return ["+define+" + as_tcl_value(define) for define in defines]

    def get_parameter_commands(self, parameters):
        return ["-g" + name + "=" + str(value) for name, value in parameters.items()]

    def build_command(self):

        do_script = "\nonerror {\n quit -code 1 \n} \n"

        out_file = os.path.join(self.build_dir, self.library_name, self.library_name + ".lib")

        if self.outdated(out_file, self.verilog_sources + self.vhdl_sources) or self.always:

            do_script += "alib {RTL_LIBRARY} \n".format(RTL_LIBRARY=as_tcl_value(self.library_name))

            if self.vhdl_sources:
                do_script += "acom -work {RTL_LIBRARY} {EXTRA_ARGS} {VHDL_SOURCES}\n".format(
                    RTL_LIBRARY=as_tcl_value(self.library_name),
                    VHDL_SOURCES=" ".join(as_tcl_value(v) for v in self.vhdl_sources),
                    EXTRA_ARGS=" ".join(as_tcl_value(v) for v in self.compile_args),
                )

            if self.verilog_sources:
                do_script += "alog -work {RTL_LIBRARY} +define+COCOTB_SIM -sv {DEFINES} {INCDIR} {EXTRA_ARGS} {VERILOG_SOURCES} \n".format(
                    RTL_LIBRARY=as_tcl_value(self.library_name),
                    VERILOG_SOURCES=" ".join(as_tcl_value(v) for v in self.verilog_sources),
                    DEFINES=" ".join(self.get_define_commands(self.defines)),
                    INCDIR=" ".join(self.get_include_commands(self.includes)),
                    EXTRA_ARGS=" ".join(as_tcl_value(v) for v in self.compile_args),
                )
        else:
            print("WARNING: Skipping compilation:" + out_file)

        do_file = tempfile.NamedTemporaryFile(delete=False)
        do_file.write(do_script.encode())
        do_file.close()

        return [["vsimsa"] + ["-do"] + ["do"] + [do_file.name]]

    def test_command(self):

        do_script = "\nonerror {\n quit -code 1 \n} \n"

        if self.toplevel_lang == "vhdl":
            do_script += "asim +access +w -interceptcoutput -O2 -loadvhpi {EXT_NAME} {EXTRA_ARGS} {TOPLEVEL} \n".format(
                TOPLEVEL=as_tcl_value(self.hdl_topmodule),
                EXT_NAME=as_tcl_value(cocotb.config.lib_name_path("vhpi", "riviera")),
                EXTRA_ARGS=" ".join(
                    as_tcl_value(v) for v in (self.sim_args + self.get_parameter_commands(self.parameters))
                ),
            )
            if self.verilog_sources:
                self.env["GPI_EXTRA"] = cocotb.config.lib_name_path("vpi", "riviera") + "cocotbvpi_entry_point"
        else:
            do_script += (
                "asim +access +w -interceptcoutput -O2 -pli {EXT_NAME} {EXTRA_ARGS} {TOPLEVEL} {PLUS_ARGS} \n".format(
                    TOPLEVEL=as_tcl_value(self.hdl_topmodule),
                    EXT_NAME=as_tcl_value(cocotb.config.lib_name_path("vpi", "riviera")),
                    EXTRA_ARGS=" ".join(
                        as_tcl_value(v) for v in (self.sim_args + self.get_parameter_commands(self.parameters))
                    ),
                    PLUS_ARGS=" ".join(as_tcl_value(v) for v in self.plus_args),
                )
            )
            if self.vhdl_sources:
                self.env["GPI_EXTRA"] = cocotb.config.lib_name_path("vhpi", "riviera") + ":cocotbvhpi_entry_point"

        if self.waves:
            do_script += "log -recursive /*;"

        do_script += "run -all \nexit"

        do_file = tempfile.NamedTemporaryFile(delete=False)
        do_file.write(do_script.encode())
        do_file.close()

        return [["vsimsa"] + ["-do"] + ["do"] + [do_file.name]]


class Verilator(Simulator):
    def __init__(self, *argv, **kwargs):
        super().__init__(*argv, **kwargs)

    @staticmethod
    def check_simulator():
        if find_executable("verilator") is None:
            raise SystemExit("ERROR: verilator exacutable not found!")

    @staticmethod
    def get_include_commands(includes):
        return ["-I" + dir for dir in includes]

    @staticmethod
    def get_define_commands(defines):
        return ["-D" + define for define in defines]

    def get_parameter_commands(self, parameters):
        return ["-G" + name + "=" + str(value) for name, value in parameters.items()]

    def build_command(self):

        if self.vhdl_sources:
            raise ValueError("This simulator does not support VHDL")

        if self.hdl_topmodule is None:
            raise ValueError("This simulator requires hdl_topmodule parameter to be specified")

        cmd = []

        verilator_cpp = os.path.join(os.path.dirname(cocotb.__file__), "share", "lib", "verilator", "verilator.cpp")

        verilator_exec = find_executable("verilator")

        cmd.append(
            [
                "perl",
                verilator_exec,
                "-cc",
                "--exe",
                "-Mdir",
                self.build_dir,
                "-DCOCOTB_SIM=1",
                "--top-module",
                self.hdl_topmodule,
                "--vpi",
                "--public-flat-rw",
                "--prefix",
                "Vtop",
                "-o",
                self.hdl_topmodule,
                "-LDFLAGS",
                "-Wl,-rpath,{LIB_DIR} -L{LIB_DIR} -lcocotbvpi_verilator".format(LIB_DIR=cocotb.config.libs_dir),
            ]
            + self.compile_args
            + self.get_define_commands(self.defines)
            + self.get_include_commands(self.includes)
            + self.get_parameter_commands(self.parameters)
            + [verilator_cpp]
            + self.verilog_sources
        )

        cmd.append(["make", "-C", self.build_dir, "-f", "Vtop.mk"])

        return cmd

    def test_command(self):
        out_file = os.path.join(self.build_dir, self.hdl_topmodule)
        return [[out_file] + self.plus_args]


def get_runner(simulator_name):

    sim_name = simulator_name.lower()
    supported_sims = {
        "icarus": Icarus,
        "questa": Questa,
        "ghdl": Ghdl,
        "riviera": Riviera,
        "verilator": Verilator,
    }  # TODO: "ius", "xcelium", "vcs"
    try:
        return supported_sims[sim_name]
    except KeyError:
        raise NotImplementedError("Set SIM variable. Supported: " + ", ".join(supported_sims)) from None


def clean(recursive=False):
    dir = os.getcwd()

    def rm_clean():
        build_dir = os.path.join(dir, "sim_build")
        if os.path.isdir(build_dir):
            print("INFO: Removing:", build_dir)
            shutil.rmtree(build_dir, ignore_errors=True)

    rm_clean()

    if recursive:
        for dir, _, _ in os.walk(dir):
            rm_clean()
