************************
Profiling Testbench Code
************************

cocotb provides two ways to profile your testbench code (and cocotb itself).
One is by using the `built-in tracing profilers in Python <https://docs.python.org/3/library/profile.html>`_,
and the other is by using a sampling profiler such as `py-spy <https://github.com/benfred/py-spy>`_.

``cProfile`` tracing profiler
=============================

The built-in `cProfile` profiler is a tracing profiler that records every function call and its duration.
This is capable of a very high degree of accuracy, but it can also introduce significant execution overhead.
Additionally, it is only capable of profiling Python code, so it will not capture time spent in cocotb's C++ code.

To profile a test run, set the :envvar:`COCOTB_ENABLE_PROFILING` to ``1`` before running your tests.
This will create a file named ``cocotb.prof`` in the directory where the test was run.

.. code-block:: bash

   export COCOTB_ENABLE_PROFILING=1

   pytest
   # or
   make

There are many ways to view the resulting profile data, but one of the most common is to use the `snakeviz <https://jiffyclub.github.io/snakeviz/>`_ tool to visualize the data in a web browser.

.. code-block:: bash

   pip install snakeviz
   snakeviz cocotb.prof


``py-spy`` sampling profiler
============================

A sampling profiler such as ``py-spy`` is not as accurate as a tracing profiler,
but, in general, it has less execution overhead than a tracing profiler, which may be preferable for long-running simulations.
Additionally, some profilers such as ``py-spy`` are able to capture time spent in C++ code, which can be useful for profiling extension modules.

To profile with py-spy, prefix the simulation command with py-spy using :envvar:`SIM_CMD_PREFIX`.

.. code-block:: bash

    export SIM_CMD_PREFIX="py-spy record --format speedscope -o profile.ss --"

    pytest
    # or
    make

It's recommended to use the ``speedscope`` output format which provides a more interactive visualization of the profile data.
You can open the output file in the `speedscope <https://www.speedscope.app/>`_ website, or you can view it locally by installing speedscope.
This requires you `install Node.js and npm <https://docs.npmjs.com/downloading-and-installing-node-js-and-npm>`_ first.

.. code-block:: bash

    npm install -g speedscope
    speedscope profile.ss
