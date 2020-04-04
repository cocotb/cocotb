# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import subprocess
import os
import sys
import tempfile
import re
import cocotb
import logging
import shutil
from xml.etree import cElementTree as ET
import threading
import signal
import cocotb._vendor.find_libpython as find_libpython
import cocotb.config

from distutils.spawn import find_executable
from distutils.sysconfig import get_config_var

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
    def __init__(
        self,
        toplevel,
        module,
        work_dir=None,
        python_search=None,
        toplevel_lang="verilog",
        verilog_sources=None,
        vhdl_sources=None,
        includes=None,
        defines=None,
        parameters=None,
        compile_args=None,
        sim_args=None,
        extra_args=None,
        plus_args=None,
        force_compile=False,
        testcase=None,
        sim_build="sim_build",
        seed=None,
        extra_env=None,
        compile_only=False,
        waves=None,
        gui=False
    ):

        self.logger = logging.getLogger()

        self.sim_dir = os.path.abspath(sim_build)
        os.makedirs(self.sim_dir, exist_ok=True)

        self.lib_dir = os.path.join(os.path.dirname(cocotb.__file__), "libs")

        self.lib_ext = "so"
        if os.name == "nt":
            self.lib_ext = "dll"

        if isinstance(module, str):
            self.module = module
        else:
            self.module = ",".join(module)

        self.work_dir = self.sim_dir

        if work_dir is not None:
            absworkdir = os.path.abspath(work_dir)
            if os.path.isdir(absworkdir):
                self.work_dir = absworkdir

        if python_search is None:
            python_search = []

        self.python_search = python_search

        self.toplevel = toplevel
        self.toplevel_lang = toplevel_lang

        if verilog_sources is None:
            verilog_sources = []

        self.verilog_sources = self.get_abs_paths(verilog_sources)

        if vhdl_sources is None:
            vhdl_sources = []

        self.vhdl_sources = self.get_abs_paths(vhdl_sources)

        if includes is None:
            includes = []

        self.includes = self.get_abs_paths(includes)

        if defines is None:
            defines = []

        self.defines = defines

        if parameters is None:
            parameters = {}

        self.parameters = parameters

        if compile_args is None:
            compile_args = []

        if extra_args is None:
            extra_args = []

        self.compile_args = compile_args + extra_args

        if sim_args is None:
            sim_args = []

        self.sim_args = sim_args + extra_args

        if plus_args is None:
            plus_args = []

        self.plus_args = plus_args
        self.force_compile = force_compile
        self.compile_only = compile_only

        # by copy since we modify
        self.env = dict(extra_env) if extra_env is not None else {}

        if testcase is not None:
            self.env["TESTCASE"] = testcase

        if seed is not None:
            self.env["RANDOM_SEED"] = str(seed)

        if waves is None:
            self.waves = bool(int(os.getenv("WAVES", 0)))
        else:
            self.waves = bool(waves)

        self.gui = gui

        # Catch SIGINT and SIGTERM
        self.old_sigint_h = signal.getsignal(signal.SIGINT)
        self.old_sigterm_h = signal.getsignal(signal.SIGTERM)

        # works only if main thread
        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGINT, self.exit_gracefully)
            signal.signal(signal.SIGTERM, self.exit_gracefully)

        self.process = None

    def set_env(self):

        for e in os.environ:
            self.env[e] = os.environ[e]

        self.env["LIBPYTHON_LOC"] = find_libpython.find_libpython()

        self.env["PATH"] += os.pathsep + self.lib_dir

        self.env["PYTHONPATH"] = os.pathsep.join(sys.path)
        for path in self.python_search:
            self.env["PYTHONPATH"] += os.pathsep + path

        self.env["PYTHONHOME"] = get_config_var("prefix")

        self.env["TOPLEVEL"] = self.toplevel
        self.env["MODULE"] = self.module

        if not os.path.exists(self.sim_dir):
            os.makedirs(self.sim_dir)

    def build_command(self):
        raise NotImplementedError()

    def run(self):

        sys.tracebacklimit = 0  # remove not needed traceback from assert

        # TODO: This probably need to be unique for multiple/parallel runs
        results_xml_file = os.getenv("COCOTB_RESULTS_FILE",os.path.join(self.sim_dir ,"results.xml"))

        cmds = self.build_command()
        self.set_env()
        self.execute(cmds)

        if not self.compile_only:
            results_file_exist = os.path.isfile(results_xml_file)
            assert results_file_exist, "Simulation terminated abnormally. Results file not found."

            tree = ET.parse(results_xml_file)
            for ts in tree.iter("testsuite"):
                for tc in ts.iter("testcase"):
                    for failure in tc.iter("failure"):
                        assert False, '{} class="{}" test="{}" error={}'.format(
                            failure.get("message"), tc.get("classname"), tc.get("name"), failure.get("stdout"),
                        )

        print("Results file: %s" % results_xml_file)
        return results_xml_file

    def get_include_commands(self, includes):
        raise NotImplementedError()

    def get_define_commands(self, defines):
        raise NotImplementedError()

    def get_parameter_commands(self, parameters):
        raise NotImplementedError()

    def get_abs_paths(self, paths):
        paths_abs = []
        for path in paths:
            if os.path.isabs(path):
                paths_abs.append(os.path.abspath(path))
            else:
                paths_abs.append(os.path.abspath(os.path.join(os.getcwd(), path)))

        return paths_abs

    def execute(self, cmds):
        self.set_env()
        for cmd in cmds:
            self.logger.info("Running command: " + " ".join(cmd))

            # TODO: create at thread to handle stderr and log as error?
            # TODO: log forwarding

            process = subprocess.run(cmd, cwd=self.work_dir, env=self.env)

            if process.returncode != 0:
                raise RuntimeError(
                    "Process '%s' termindated with error %d"
                    % (process.args[0], process.returncode)
                )

    def outdated(self, output, dependencies):

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
        assert False, "Exiting pid: {} with signum: {}".format(str(pid), str(signum))


class Icarus(Simulator):
    def __init__(self, *argv, **kwargs):
        super(Icarus, self).__init__(*argv, **kwargs)

        if self.vhdl_sources:
            raise ValueError("This simulator does not support VHDL")

        self.sim_file = os.path.join(self.sim_dir, self.toplevel + ".vvp")

    def get_include_commands(self, includes):
        include_cmd = []
        for dir in includes:
            include_cmd.append("-I")
            include_cmd.append(dir)

        return include_cmd

    def get_define_commands(self, defines):
        defines_cmd = []
        for define in defines:
            defines_cmd.append("-D")
            defines_cmd.append(define)

        return defines_cmd

    def get_parameter_commands(self, parameters):
        parameters_cmd = []
        for name, value in parameters.items():
            parameters_cmd.append("-P")
            parameters_cmd.append(self.toplevel + "." + name + "=" + str(value))

        return parameters_cmd

    def compile_command(self):

        cmd_compile = (
            ["iverilog", "-o", self.sim_file, "-D", "COCOTB_SIM=1", "-s", self.toplevel, "-g2012"]
            + self.get_define_commands(self.defines)
            + self.get_include_commands(self.includes)
            + self.get_parameter_commands(self.parameters)
            + self.compile_args
            + self.verilog_sources
        )

        return cmd_compile

    def run_command(self):
        return (
            ["vvp", "-M", self.lib_dir, "-m", cocotb.config.lib_name("vpi", "icarus")]
            + self.sim_args
            + [self.sim_file]
            + self.plus_args
        )

    def build_command(self):
        if self.waves:
            dump_mod_name = "iverilog_dump"
            dump_file_name = self.toplevel+".fst"
            dump_mod_file_name = os.path.join(self.sim_dir, dump_mod_name+".v")

            if not os.path.exists(dump_mod_file_name):
                with open(dump_mod_file_name, 'w') as f:
                    f.write("module iverilog_dump();\n")
                    f.write("initial begin\n")
                    f.write("    $dumpfile(\"%s\");\n" % dump_file_name)
                    f.write("    $dumpvars(0, %s);\n" % self.toplevel)
                    f.write("end\n")
                    f.write("endmodule\n")

            self.verilog_sources.append(dump_mod_file_name)
            self.compile_args.extend(["-s", dump_mod_name])
            self.plus_args.append("-fst")

        cmd = []
        if self.outdated(self.sim_file, self.verilog_sources) or self.force_compile:
            cmd.append(self.compile_command())
        else:
            self.logger.warning("Skipping compilation:" + self.sim_file)

        # TODO: check dependency?
        if not self.compile_only:
            cmd.append(self.run_command())

        return cmd


class Questa(Simulator):
    def get_include_commands(self, includes):
        include_cmd = []
        for dir in includes:
            include_cmd.append("+incdir+" + as_tcl_value(dir))

        return include_cmd

    def get_define_commands(self, defines):
        defines_cmd = []
        for define in defines:
            defines_cmd.append("+define+" + as_tcl_value(define))

        return defines_cmd

    def get_parameter_commands(self, parameters):
        parameters_cmd = []
        for name, value in parameters.items():
            parameters_cmd.append("-g" + name + "=" + str(value))

        return parameters_cmd

    def build_command(self):

        self.rtl_library = self.toplevel

        cmd = []

        if self.vhdl_sources:
            do_script = "vlib {RTL_LIBRARY}; vcom -mixedsvvh {FORCE} -work {RTL_LIBRARY} {EXTRA_ARGS} {VHDL_SOURCES}; quit".format(
                RTL_LIBRARY=as_tcl_value(self.rtl_library),
                VHDL_SOURCES=" ".join(as_tcl_value(v) for v in self.vhdl_sources),
                EXTRA_ARGS=" ".join(as_tcl_value(v) for v in self.compile_args),
                FORCE=""  # if self.force_compile else "-incr", # No support for -incr
            )
            cmd.append(["vsim"] + ["-c"] + ["-do"] + [do_script])

        if self.verilog_sources:
            do_script = "vlib {RTL_LIBRARY}; vlog -mixedsvvh {FORCE} -work {RTL_LIBRARY} +define+COCOTB_SIM -sv {DEFINES} {INCDIR} {EXTRA_ARGS} {VERILOG_SOURCES}; quit".format(
                RTL_LIBRARY=as_tcl_value(self.rtl_library),
                VERILOG_SOURCES=" ".join(as_tcl_value(v) for v in self.verilog_sources),
                DEFINES=" ".join(self.get_define_commands(self.defines)),
                INCDIR=" ".join(self.get_include_commands(self.includes)),
                EXTRA_ARGS=" ".join(as_tcl_value(v) for v in self.compile_args),
                FORCE="" if self.force_compile else "-incr",
            )
            cmd.append(["vsim"] + ["-c"] + ["-do"] + [do_script])

        if not self.compile_only:
            if self.toplevel_lang == "vhdl":
                do_script = "vsim -onfinish {ONFINISH} -foreign {EXT_NAME} {EXTRA_ARGS} {RTL_LIBRARY}.{TOPLEVEL};".format(
                    ONFINISH="stop" if self.gui else "exit",
                    RTL_LIBRARY=as_tcl_value(self.rtl_library),
                    TOPLEVEL=as_tcl_value(self.toplevel),
                    EXT_NAME=as_tcl_value(
                        "cocotb_init {}".format(cocotb.config.lib_name_path("fli", "questa"))
                    ),
                    EXTRA_ARGS=" ".join(as_tcl_value(v) for v in (self.sim_args + self.get_parameter_commands(self.parameters))),
                )

                if self.verilog_sources:
                    self.env["GPI_EXTRA"] = cocotb.config.lib_name_path("vpi", "questa")+":cocotbvpi_entry_point"

            else:
                do_script = "vsim -onfinish {ONFINISH} -pli {EXT_NAME} {EXTRA_ARGS} {RTL_LIBRARY}.{TOPLEVEL} {PLUS_ARGS};".format(
                    ONFINISH="stop" if self.gui else "exit",
                    RTL_LIBRARY=as_tcl_value(self.rtl_library),
                    TOPLEVEL=as_tcl_value(self.toplevel),
                    EXT_NAME=as_tcl_value(cocotb.config.lib_name_path("vpi", "questa")),
                    EXTRA_ARGS=" ".join(as_tcl_value(v) for v in (self.sim_args + self.get_parameter_commands(self.parameters))),
                    PLUS_ARGS=" ".join(as_tcl_value(v) for v in self.plus_args),
                )

                if self.vhdl_sources:
                    self.env["GPI_EXTRA"] = cocotb.config.lib_name_path("fli", "questa")+":cocotbfli_entry_point"

            if self.waves:
                do_script += "log -recursive /*;"

            if not self.gui:
                do_script += "run -all; quit"

            cmd.append(["vsim"] + (["-gui"] if self.gui else ["-c"]) + ["-do"] + [do_script])

        return cmd


class Ius(Simulator):
    def __init__(self, *argv, **kwargs):
        super(Ius, self).__init__(*argv, **kwargs)

        self.env["GPI_EXTRA"] = cocotb.config.lib_name_path("vhpi", "ius")+":cocotbvhpi_entry_point"

    def get_include_commands(self, includes):
        include_cmd = []
        for dir in includes:
            include_cmd.append("-incdir")
            include_cmd.append(dir)

        return include_cmd

    def get_define_commands(self, defines):
        defines_cmd = []
        for define in defines:
            defines_cmd.append("-define")
            defines_cmd.append(define)

        return defines_cmd

    def get_parameter_commands(self, parameters):
        parameters_cmd = []
        for name, value in parameters.items():
            if self.toplevel_lang == "vhdl":
                parameters_cmd.append("-generic")
                parameters_cmd.append("\"" + self.toplevel + "." + name + "=>" + str(value) + "\"")
            else:
                parameters_cmd.append("-defparam")
                parameters_cmd.append("\"" + self.toplevel + "." + name + "=" + str(value) + "\"")

        return parameters_cmd

    def build_command(self):

        out_file = os.path.join(self.sim_dir, "INCA_libs", "history")

        cmd = []

        if self.outdated(out_file, self.verilog_sources + self.vhdl_sources) or self.force_compile:
            cmd_elab = (
                [
                    "irun",
                    "-64",
                    "-elaborate",
                    "-v93",
                    "-define",
                    "COCOTB_SIM=1",
                    "-loadvpi",
                    cocotb.config.lib_name_path("vpi", "ius") + ":vlog_startup_routines_bootstrap",
                    "-plinowarn",
                    "-access",
                    "+rwc",
                    "-top",
                    self.toplevel,
                ]
                + self.get_define_commands(self.defines)
                + self.get_include_commands(self.includes)
                + self.get_parameter_commands(self.parameters)
                + self.compile_args
                + self.verilog_sources
                + self.vhdl_sources
            )
            cmd.append(cmd_elab)

        else:
            self.logger.warning("Skipping compilation:" + out_file)

        if not self.compile_only:
            cmd_run = ["irun", "-64", "-R", ("-gui" if self.gui else "")] + self.sim_args + self.get_parameter_commands(self.parameters) + self.plus_args
            cmd.append(cmd_run)

        return cmd


class Xcelium(Simulator):
    def __init__(self, *argv, **kwargs):
        super(Xcelium, self).__init__(*argv, **kwargs)

        self.env["GPI_EXTRA"] = cocotb.config.lib_name_path("vhpi", "ius") + ":cocotbvhpi_entry_point"

    def get_include_commands(self, includes):
        include_cmd = []
        for dir in includes:
            include_cmd.append("-incdir")
            include_cmd.append(dir)

        return include_cmd

    def get_define_commands(self, defines):
        defines_cmd = []
        for define in defines:
            defines_cmd.append("-define")
            defines_cmd.append(define)

        return defines_cmd

    def get_parameter_commands(self, parameters):
        parameters_cmd = []
        for name, value in parameters.items():
            if self.toplevel_lang == "vhdl":
                parameters_cmd.append("-generic")
                parameters_cmd.append("\"" + self.toplevel + "." + name + "=>" + str(value) + "\"")
            else:
                parameters_cmd.append("-defparam")
                parameters_cmd.append("\"" + self.toplevel + "." + name + "=" + str(value) + "\"")

        return parameters_cmd

    def build_command(self):

        out_file = os.path.join(self.sim_dir, "INCA_libs", "history")

        cmd = []

        if self.outdated(out_file, self.verilog_sources + self.vhdl_sources) or self.force_compile:
            cmd_elab = (
                [
                    "xrun",
                    "-64",
                    "-v93",
                    "-elaborate",
                    "-define",
                    "COCOTB_SIM=1",
                    "-loadvpi",
                    cocotb.config.lib_name_path("vpi", "ius") + ":vlog_startup_routines_bootstrap",
                    "-plinowarn",
                    "-access",
                    "+rwc",
                    "-top",
                    self.toplevel,
                ]
                + self.get_define_commands(self.defines)
                + self.get_include_commands(self.includes)
                + self.get_parameter_commands(self.parameters)
                + self.compile_args
                + self.verilog_sources
                + self.vhdl_sources
            )
            cmd.append(cmd_elab)

        else:
            self.logger.warning("Skipping compilation:" + out_file)

        if not self.compile_only:
            cmd_run = ["xrun", "-64", "-R", ("-gui" if self.gui else "")] + self.sim_args + self.get_parameter_commands(self.parameters) + self.plus_args
            cmd.append(cmd_run)

        return cmd


class Vcs(Simulator):
    def get_include_commands(self, includes):
        include_cmd = []
        for dir in includes:
            include_cmd.append("+incdir+" + dir)

        return include_cmd

    def get_define_commands(self, defines):
        defines_cmd = []
        for define in defines:
            defines_cmd.append("+define+" + define)

        return defines_cmd

    def get_parameter_commands(self, parameters):
        parameters_cmd = []
        for name, value in parameters.items():
            parameters_cmd.append("-pvalue+" + self.toplevel + "/" + name + "=" + str(value))

        return parameters_cmd

    def build_command(self):

        pli_cmd = "acc+=rw,wn:*"

        cmd = []

        do_file_path = os.path.join(self.sim_dir, "pli.tab")
        with open(do_file_path, "w") as pli_file:
            pli_file.write(pli_cmd)

        cmd_build = (
            [
                "vcs",
                "-full64",
                "-debug",
                "+vpi",
                "-P",
                "pli.tab",
                "-sverilog",
                "+define+COCOTB_SIM=1",
                "-load",
                cocotb.config.lib_name_path("vpi", "vcs"),
            ]
            + self.get_define_commands(self.defines)
            + self.get_include_commands(self.includes)
            + self.get_parameter_commands(self.parameters)
            + self.compile_args
            + self.verilog_sources
        )
        cmd.append(cmd_build)

        if not self.compile_only:
            cmd_run = [os.path.join(self.sim_dir, "simv"), "+define+COCOTB_SIM=1"] + self.sim_args
            cmd.append(cmd_run)

        if self.gui:
            cmd.append("-gui")  # not tested!

        return cmd


class Ghdl(Simulator):
    def get_include_commands(self, includes):
        include_cmd = []
        for dir in includes:
            include_cmd.append("-I")
            include_cmd.append(dir)

        return include_cmd

    def get_define_commands(self, defines):
        defines_cmd = []
        for define in defines:
            defines_cmd.append("-D")
            defines_cmd.append(define)

    def get_parameter_commands(self, parameters):
        parameters_cmd = []
        for name, value in parameters.items():
            parameters_cmd.append("-g" + name + "=" + str(value))

        return parameters_cmd

    def build_command(self):

        cmd = []

        out_file = os.path.join(self.sim_dir, self.toplevel)

        if self.outdated(out_file, self.verilog_sources + self.vhdl_sources) or self.force_compile:
            for source_file in self.vhdl_sources:
                cmd.append(["ghdl", "-i"] + self.compile_args + [source_file])

            cmd_elaborate = ["ghdl", "-m"] + self.compile_args + [self.toplevel]
            cmd.append(cmd_elaborate)

        if self.waves:
            self.sim_args.append("--wave=" + self.toplevel + ".ghw")

        cmd_run = (
            ["ghdl", "-r"] + self.compile_args + [self.toplevel]
            + ["--vpi=" + cocotb.config.lib_name_path("vpi", "ghdl")]
            + self.sim_args
            + self.get_parameter_commands(self.parameters)
        )

        if not self.compile_only:
            cmd.append(cmd_run)

        return cmd


class Riviera(Simulator):
    def get_include_commands(self, includes):
        include_cmd = []
        for dir in includes:
            include_cmd.append("+incdir+" + as_tcl_value(dir))

        return include_cmd

    def get_define_commands(self, defines):
        defines_cmd = []
        for define in defines:
            defines_cmd.append("+define+" + as_tcl_value(define))

        return defines_cmd

    def get_parameter_commands(self, parameters):
        parameters_cmd = []
        for name, value in parameters.items():
            parameters_cmd.append("-g" + name + "=" + str(value))

        return parameters_cmd

    def build_command(self):

        self.rtl_library = self.toplevel

        do_script = "\nonerror {\n quit -code 1 \n} \n"

        out_file = os.path.join(self.sim_dir, self.rtl_library, self.rtl_library + ".lib")

        if self.outdated(out_file, self.verilog_sources + self.vhdl_sources) or self.force_compile:

            do_script += "alib {RTL_LIBRARY} \n".format(RTL_LIBRARY=as_tcl_value(self.rtl_library))

            if self.vhdl_sources:
                do_script += "acom -work {RTL_LIBRARY} {EXTRA_ARGS} {VHDL_SOURCES}\n".format(
                    RTL_LIBRARY=as_tcl_value(self.rtl_library),
                    VHDL_SOURCES=" ".join(as_tcl_value(v) for v in self.vhdl_sources),
                    EXTRA_ARGS=" ".join(as_tcl_value(v) for v in self.compile_args),
                )

            if self.verilog_sources:
                do_script += "alog -work {RTL_LIBRARY} +define+COCOTB_SIM -sv {DEFINES} {INCDIR} {EXTRA_ARGS} {VERILOG_SOURCES} \n".format(
                    RTL_LIBRARY=as_tcl_value(self.rtl_library),
                    VERILOG_SOURCES=" ".join(as_tcl_value(v) for v in self.verilog_sources),
                    DEFINES=" ".join(self.get_define_commands(self.defines)),
                    INCDIR=" ".join(self.get_include_commands(self.includes)),
                    EXTRA_ARGS=" ".join(as_tcl_value(v) for v in self.compile_args),
                )
        else:
            self.logger.warning("Skipping compilation:" + out_file)

        if not self.compile_only:
            if self.toplevel_lang == "vhdl":
                do_script += "asim +access +w -interceptcoutput -O2 -loadvhpi {EXT_NAME} {EXTRA_ARGS} {RTL_LIBRARY}.{TOPLEVEL} \n".format(
                    RTL_LIBRARY=as_tcl_value(self.rtl_library),
                    TOPLEVEL=as_tcl_value(self.toplevel),
                    EXT_NAME=as_tcl_value(cocotb.config.lib_name_path("vhpi", "riviera")),
                    EXTRA_ARGS=" ".join(as_tcl_value(v) for v in (self.sim_args + self.get_parameter_commands(self.parameters))),
                )
                if self.verilog_sources:
                    self.env["GPI_EXTRA"] = cocotb.config.lib_name_path("vpi", "riviera") + "cocotbvpi_entry_point"
            else:
                do_script += "asim +access +w -interceptcoutput -O2 -pli {EXT_NAME} {EXTRA_ARGS} {RTL_LIBRARY}.{TOPLEVEL} {PLUS_ARGS} \n".format(
                    RTL_LIBRARY=as_tcl_value(self.rtl_library),
                    TOPLEVEL=as_tcl_value(self.toplevel),
                    EXT_NAME=as_tcl_value(cocotb.config.lib_name_path("vpi", "riviera")),
                    EXTRA_ARGS=" ".join(as_tcl_value(v) for v in (self.sim_args + self.get_parameter_commands(self.parameters))),
                    PLUS_ARGS=" ".join(as_tcl_value(v) for v in self.plus_args),
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
        super(Verilator, self).__init__(*argv, **kwargs)

        if self.vhdl_sources:
            raise ValueError("This simulator does not support VHDL")

        self.env['CXXFLAGS'] = self.env.get('CXXFLAGS', "") + " -std=c++11"

    def get_include_commands(self, includes):
        include_cmd = []
        for dir in includes:
            include_cmd.append("-I" + dir)

        return include_cmd

    def get_define_commands(self, defines):
        defines_cmd = []
        for define in defines:
            defines_cmd.append("-D" + define)

        return defines_cmd

    def get_parameter_commands(self, parameters):
        parameters_cmd = []
        for name, value in parameters.items():
            parameters_cmd.append("-G" + name + "=" + str(value))

        return parameters_cmd

    def build_command(self):

        cmd = []

        out_file = os.path.join(self.sim_dir, self.toplevel)
        verilator_cpp = os.path.join(os.path.dirname(os.path.dirname(self.lib_dir)), "share", "verilator.cpp")
        verilator_cpp = os.path.join(os.path.dirname(cocotb.__file__), "share", "lib", "verilator", "verilator.cpp")

        verilator_exec = find_executable("verilator")
        if verilator_exec is None:
            raise ValueError("Verilator executable not found.")

        if self.waves:
            self.compile_args += ["--trace-fst", "--trace-structs"]

        cmd.append(
            [
                "perl",
                verilator_exec,
                "-cc",
                "--exe",
                "-Mdir",
                self.sim_dir,
                "-DCOCOTB_SIM=1",
                "--top-module",
                self.toplevel,
                "--vpi",
                "--public-flat-rw",
                "--prefix",
                "Vtop",
                "-o",
                self.toplevel,
                "-LDFLAGS",
                "-Wl,-rpath,{LIB_DIR} -L{LIB_DIR} -lcocotbvpi_verilator".format(LIB_DIR=self.lib_dir),
            ]
            + self.compile_args
            + self.get_define_commands(self.defines)
            + self.get_include_commands(self.includes)
            + self.get_parameter_commands(self.parameters)
            + [verilator_cpp]
            + self.verilog_sources
        )

        cmd.append(["make", "-C", self.sim_dir, "-f", "Vtop.mk"])

        if not self.compile_only:
            cmd.append([out_file] + self.plus_args)

        return cmd


def run(**kwargs):

    sim_env = os.getenv("SIM", "icarus")

    supported_sim = ["icarus", "questa", "ius", "xcelium", "vcs", "ghdl", "riviera", "verilator"]
    if sim_env not in supported_sim:
        raise NotImplementedError("Set SIM variable. Supported: " + ", ".join(supported_sim))

    if sim_env == "icarus":
        sim = Icarus(**kwargs)
    elif sim_env == "questa":
        sim = Questa(**kwargs)
    elif sim_env == "ius":
        sim = Ius(**kwargs)
    elif sim_env == "xcelium":
        sim = Xcelium(**kwargs)
    elif sim_env == "vcs":
        sim = Vcs(**kwargs)
    elif sim_env == "ghdl":
        sim = Ghdl(**kwargs)
    elif sim_env == "riviera":
        sim = Riviera(**kwargs)
    elif sim_env == "verilator":
        sim = Verilator(**kwargs)

    return sim.run()


def clean(recursive=False):
    dir = os.getcwd()

    def rm_clean():
        sim_build_dir = os.path.join(dir, "sim_build")
        if os.path.isdir(sim_build_dir):
            print("Removing:", sim_build_dir)
            shutil.rmtree(sim_build_dir, ignore_errors=True)

    rm_clean()

    if recursive:
        for dir, _, _ in os.walk(dir):
            rm_clean()
