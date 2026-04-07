# Cocotb Development Environment in a Dev Container

The Dev Container provides a ready-to-code development environment for cocotb on Windows, Mac, or Linux.
Dev Containers combine VS Code with (Docker) containers and configuration within the cocotb repository.

By default, Dev Containers cannot access files on your local machine;
if you want to use proprietary simulators installed on your machine, you might be better off with a development environment on your machine itself.

## What's included in the Dev Container?

* Ubuntu 24.04
* Compilers: GCC and clang
* Open-source simulators: GHDL, Icarus Verilog, Verilator, NVC
* Productivity tools: GDB, LLDB, Valgrind, [Bear](https://github.com/rizsotto/Bear)

## Getting started

You need VS Code and the Dev Containers extension to run the Dev Container on your local machine.
Follow the [Dev Containers Getting Started documentation](https://code.visualstudio.com/docs/devcontainers/containers#_getting-started) documentation to install all required tools.

Then start the Dev Container:
* Open VS Code
* Open the command palette (F1)
* Type `Dev Containers: Clone Repository in Container Volume...` and press ENTER.
* Enter the repository URL `https://github.com/cocotb/cocotb` and press ENTER again.
* Wait for a short moment until the Dev Container is ready to be used.

Note: On Linux you can alternatively clone the Git repository on your local machine and open the folder in a container.
We don't recommend that on Windows or Mac to get good filesystem performance ([learn more](https://code.visualstudio.com/remote/advancedcontainers/improve-performance)).

After the Dev Container startup completed **open a new terminal** to run a first cocotb test.
Note: *Do not* reuse the `Welcome to Codespaces` terminal you might see -- it does not have an active Python venv and commands will fail.

```
cd examples/simple_dff
make WAVES=1 SIM=iverlog
code sim_build/dff.fst
```
