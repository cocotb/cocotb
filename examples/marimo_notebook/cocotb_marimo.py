# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "matplotlib",
# ]
# ///

import marimo

__generated_with = "0.8.7"
app = marimo.App(
    width="medium",
    app_title="cocotb and marimo",
    layout_file="layouts/cocotb_marimo.slides.json",
)


@app.cell
def __():
    # This file is public domain, it can be freely copied without restrictions.
    # SPDX-License-Identifier: CC0-1.0
    return


@app.cell(hide_code=True)
def __():
    # /// script
    # requires-python = ">=3.6"
    # dependencies = ["cocotb>=2", "marimo", "matplotlib", pytest"]
    # ///
    import marimo as mo
    return mo,


@app.cell(hide_code=True)
def __(mo):
    mo.md(
        """
        # cocotb in a marimo notebook
        [cocotb.org](https://cocotb.org) and [marimo.io](https://marimo.io)
        """
    )
    return


@app.cell
def __():
    # importing packages
    import os
    import sys
    from pathlib import Path

    import cocotb
    return Path, cocotb, os, sys


@app.cell
def __(Path, __file__, cocotb, os, sys):
    # setting up testbench
    os.environ["COCOTB_ANSI_OUTPUT"] = "1"  # colorize output
    proj_path = Path(__file__).resolve().parent
    my_path = str(proj_path / ".." / "doc_examples" / "quickstart")
    if my_path not in sys.path:
        print(f"Prepending {sys.path!r} with {my_path!r}")
        sys.path.insert(0, my_path)

    sources = [Path(my_path) / "my_design.sv"]
    runner = cocotb.runner.get_runner(os.getenv("SIM", "icarus"))
    return my_path, proj_path, runner, sources


@app.cell
def __(runner, sources):
    # building the HDL sources
    runner.build(
        sources=sources,
        hdl_toplevel="my_design",
        always=True,
    )
    return


@app.cell
def __(proj_path, runner):
    # running the test
    runner.test(
        hdl_toplevel="my_design",
        test_module="test_my_design,",
        results_xml=(proj_path / "results.xml"),
    )
    return


@app.cell
def __(cocotb, proj_path):
    # plotting test results
    import matplotlib.pyplot as plt

    passed, failed = cocotb.runner.get_results(proj_path / "results.xml")
    plt.bar("Tests", passed, color="tab:green")
    plt.bar("Tests", failed, bottom=passed, color="tab:red")

    plt.title("Pass/Fail")
    plt.ylabel("Count")
    plt.legend(["passed", "failed"])
    plt.tight_layout()
    plt.gcf()
    return failed, passed, plt


@app.cell
def __(mo):
    mo.image(src="https://www.cocotb.org/assets/img/cocotb-logo.svg", width=100)
    return


@app.cell
def __():
    return


@app.cell(hide_code=True)
def __(mo):
    mo.image(
        src="https://docs.marimo.io/_static/marimo-logotype-thick.svg", width=100
    )
    return


@app.cell
def __():
    return


if __name__ == "__main__":
    app.run()
