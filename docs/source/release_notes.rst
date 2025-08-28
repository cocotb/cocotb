*************
Release Notes
*************

.. spelling:word-list::
   dev

All releases are available from the `GitHub Releases Page <https://github.com/cocotb/cocotb/releases>`_.

.. include:: master-notes.rst

.. towncrier release notes start

cocotb 2.0.0b1 (2025-07-12)
===========================

This is the first beta release of the upcoming cocotb 2.0.
As indicated by the version number, this new version contains API-breaking changes that may require updates to existing testbenches.
Refer to :doc:`upgrade-2.0` to guide you through the upgrade process.

Features
--------

- Made :class:`simulator objects <cocotb.handle.SimHandleBase>` hashable. Simulator objects can now be used as :class:`dict` keys and :class:`set` items. (:pr:`2720`)
- Added the :attr:`.ValueObjectBase.is_const` property to support checking if a :class:`ValueObject` is immutable. (:pr:`2720`)
- Add a new compilation flow for Questa called ``qisqrun``. This flow uses uses the Questa Information System (QIS) for faster simulation performance, Qrun for automatic ordering of VHDL source files and Visualizer as GUI. The new flow can be enabled explicitly by passing :make:var:`SIM=questa-qisqrun <SIM>` to ``make``. Users using ``SIM=questa`` use the flow automatically if Questa 2025.2 or newer is detected. To explicitly choose the older flow (which uses ``vsim`` and friends) use ``SIM=questa-compat``. (:pr:`2852`)
- Added :func:`cocotb.parametrize`, a decorator that serves as an alternative to :class:`~cocotb.regression.TestFactory`. (:pr:`3513`)
- Added :any:`cocotb.packages` which contains handles to SystemVerilog packages in a design. (:pr:`3536`)
- The current Git revision will now be added to :data:`cocotb.__version__` for all ``dev`` versions. (:pr:`3568`)
- The :func:`cocotb.test` decorator now accepts a ``name`` argument to override the name of the test in the :class:`~cocotb.regression.RegressionManager`. (:pr:`3578`)
- Added :attr:`~cocotb.handle.HierarchyArrayObject.range`, :attr:`~cocotb.handle.HierarchyArrayObject.left`, :attr:`~cocotb.handle.HierarchyArrayObject.direction`, :attr:`~cocotb.handle.HierarchyArrayObject.right`, and :func:`len` support to :class:`~cocotb.handle.HierarchyArrayObject`. (:pr:`3655`)
- Added :meth:`.HierarchyObject._keys`, :meth:`.HierarchyObject._values`, and :meth:`.HierarchyObject._items` to help users dynamically interact with hierarchical elements of the :term:`DUT`. (:pr:`3655`)
- Add support for ``handle[sub_handle_name]`` syntax to :class:`~cocotb.handle.HierarchyObject` as a more readable alternative to :meth:`HierarchyObject._id() <cocotb.handle.HierarchyObject._id>`. (:pr:`3655`)
- :class:`~cocotb.types.Array` now supports equality with :class:`list` and :class:`tuple`. (:pr:`3659`)
- Support comparing :class:`~cocotb.types.LogicArray` with :class:`str`, :class:`list`, and :class:`tuple`. (:pr:`3696`)
- Use parameter values in generated test names of :func:`cocotb.parametrize`, which should be clearer and allow the user to better group tests using :envvar:`COCOTB_TEST_FILTER`. (:pr:`3717`)
- Support specifying arguments like in :meth:`TestFactory.add_option() <cocotb.regression.TestFactory.add_option>` in :func:`cocotb.parametrize`. (:pr:`3717`)
- Added :attr:`~cocotb.handle.LogicArrayObject.range`, :attr:`~cocotb.handle.LogicArrayObject.left`, :attr:`~cocotb.handle.LogicArrayObject.direction`, and :attr:`~cocotb.handle.LogicArrayObject.right` properties to :class:`~cocotb.handle.LogicArrayObject`. (:pr:`3733`)
- Added :attr:`~cocotb.handle.ArrayObject.range`, :attr:`~cocotb.handle.ArrayObject.left`, :attr:`~cocotb.handle.ArrayObject.direction`, and :attr:`~cocotb.handle.ArrayObject.right` properties to :class:`~cocotb.handle.ArrayObject`, :class:`~cocotb.handle.LogicArrayObject`, and :class:`~cocotb.handle.StringObject`. (:pr:`3733`)
- Added :attr:`~cocotb.handle.StringObject.range`, :attr:`~cocotb.handle.StringObject.left`, :attr:`~cocotb.handle.StringObject.direction`, and :attr:`~cocotb.handle.StringObject.right` properties to :class:`~cocotb.handle.StringObject`. (:pr:`3733`)
- Added support for using :class:`str` in assignment to :class:`~cocotb.handle.LogicObject`\ s. (:pr:`3733`)
- Setting a value with :attr:`ArrayObject.value <cocotb.handle.ArrayObject.value>` now accepts any :class:`~collections.abc.Sequence`\ -like type, such as :class:`tuple` and :class:`list`, as well as :class:`~cocotb.types.Array`. (:pr:`3733`)
- :meth:`handle.set() <cocotb.handle.ValueObjectBase.set>` was added to value-having simulation object handles as an alternative to the :attr:`~cocotb.handle.ValueObjectBase.value` property that provides correct type checking information. (:pr:`3733`)
- Introduced :attr:`cocotb.is_simulation` which is ``True`` only when the cocotb library was loaded in a simulation. (:pr:`3779`)
- The :ref:`combine_results.py <combine-results>` script now ships with the cocotb installation. (:pr:`3791`)
- Added :meth:`LogicArray.to_unsigned() <cocotb.types.LogicArray.to_unsigned>` and :meth:`LogicArray.to_signed() <cocotb.types.LogicArray.to_signed>` to convert :class:`~cocotb.types.LogicArray` into :class:`int`. (:pr:`3792`)
- Added :meth:`LogicArray.from_unsigned() <cocotb.types.LogicArray.from_unsigned>` and :meth:`LogicArray.from_signed() <cocotb.types.LogicArray.from_signed>` to construct :class:`~cocotb.types.LogicArray` from :class:`int`. (:pr:`3792`)
- Added :envvar:`COCOTB_TEST_FILTER` which filters tests like :envvar:`COCOTB_TESTCASE`, but is a regular expression to allow for more expressive test filtering. (:pr:`3841`)
- Introduced :envvar:`COCOTB_TRUST_INERTIAL_WRITES` to enable a mode where VPI/VHPI/FLI inertial writes are trusted to behave properly. Enabling this feature can lead to behavioral changes and noticeable performance improvements. Some simulators do not handle writes properly, so use this option with caution. (:pr:`3873`)
- Added :class:`cocotb.simulator.GpiClock`, a C++ clock generator implementation with higher performance due to less handshaking between Python and the GPI. :class:`~cocotb.clock.Clock` uses it automatically when it would behave identically to the Python implementation. (:pr:`3983`)
- The Siemens DSim simulator is now supported by cocotb. (:pr:`3990`)
- Added :meth:`.LogicArray.to_bytes` and :meth:`.LogicArray.from_bytes` for converting :class:`~cocotb.types.LogicArray` to and from :class:`bytes`. (:pr:`4098`)
- :class:`~cocotb.types.LogicArray` can take :class:`int` as the second positional argument as shorthand for passing ``Range(width-1, "downto", 0)`` as ``range``. (:pr:`4142`)
- :class:`~cocotb.types.Array` can take :class:`int` as the second positional argument or ``width`` keyword argument as shorthand for passing ``Range(0, "to", width-1)`` as ``range``. (:pr:`4142`)
- Allow user to specify elaboration arguments (``elab_args``) to :meth:`.Runner.build` for NVC (e.g. to enable coverage collection). (:pr:`4267`)
- Added :attr:`cocotb.types.logic_array.RESOLVE_X` which controls the default resolution behavior of ``X``, ``Z``, ``U``, ``W``, and ``-`` values in :class:`.LogicArray`\ s whenever they are converted to integers using :class:`int` casts, :meth:`.LogicArray.to_unsigned` or :meth:`.LogicArray.to_signed` without passing an argument for the ``resolve`` parameter. (:pr:`4298`)
- Adding support for resolving ``X``, ``Z``, ``U``, ``W``, and ``-`` values to :meth:`.LogicArray.to_unsigned` and :meth:`.LogicArray.to_signed`. (:pr:`4298`)
- :envvar:`PYGPI_USERS` supports multiple user modules by comma-separating them. (:pr:`4310`)
- The Makefile flow no longer requires that :ref:`cocotb-config <cocotb-config>` be located on the ``PATH``. Set :envvar:`PYTHON_BIN` if the wrong Python executable is used. (:pr:`4338`)
- Added :class:`.TaskComplete` Trigger and :attr:`.Task.complete` to get that Trigger for the Task. These are intended to replace :class:`.Join` and :meth:`.Task.join` and do not return the Tasks result when :keyword:`await`\ ed. (:pr:`4341`)
- :class:`~cocotb.triggers.ClockCycles` can be constructed by passing one of the :ref:`edge-triggers` as the ``edge_type`` argument. (:pr:`4396`)
- :class:`~cocotb.clock.Clock` now owns the driver task, so the user does not need to pass the result of :meth:`.Clock.start` to :func:`cocotb.start_soon`. Additionally, :meth:`.Clock.stop` was introduced to stop the clock driver. (:pr:`4396`)
- Add :meth:`.Clock.cycles` to wait a given number of clock cycles. (:pr:`4396`)
- :class:`~cocotb.task.Task` objects which are already created or running can be passed to :func:`cocotb.start`, :func:`cocotb.start_soon`, and :func:`cocotb.create_task` more than once. (:pr:`4396`)
- :envvar:`GPI_LOG_LEVEL` was added to control GPI loggers (``"gpi"`` and children). (:pr:`4467`)
- Guarantee that :class:`.Lock` acquisition is fair. (:pr:`4473`)
- :func:`cocotb.pass_test` was introduced to immediately end a test with a passing outcome. (:pr:`4477`)
- :class:`cocotb.handle.Immediate` was added to support :term:`no-delay deposit`\ s. (:pr:`4479`)
- :meth:`handle.get() <cocotb.handle.ValueObjectBase.get>` was added to parallel :meth:`handle.set() <cocotb.handle.ValueObjectBase.set>`. (:pr:`4479`)
- Makefile runners no longer need to specify :make:var:`SIM`, and have the simulator executable available, to run ``make clean``. (:pr:`4505`)
- Added :meth:`~.HierarchyObject._get` which returns ``None`` on failure instead of raising an exception to aid with optional signal discovery. It also accepts the optional parameter ``discovery_method`` that takes :class:`~cocotb.handle.GPIDiscovery` to specialize object discovery. (:pr:`4517`)
- Added :data:`cocotb.triggers.current_gpi_trigger` to allow the user to determine the last GPI trigger that fired. (:pr:`4549`)
- Running Tasks are now :meth:`cancelled <cocotb.task.Task.cancel>` at the end of the Test, which throws :exc:`~asyncio.CancelledError` into the Task allowing them to do cleanup actions at test end. (:pr:`4574`)
- Added :meth:`.Logic.resolve` and :meth:`.LogicArray.resolve` to resolve non-``0``/``1`` values on demand. (:pr:`4622`)
- :class:`.LogicArray` now supports :class:`bool` casts and usage in conditionals (e.g. ``if dut.data.value: ...``). (:pr:`4622`)
- The :make:var:`GUI` and :make:var:`WAVES` environment variables can be used to override the corresponding ``gui`` and ``waves`` arguments to pytest test benches. This means that they can be provided at run-time without modifying the test bench. (:pr:`4635`)
- The ``gui`` argument to :meth:`Runner.test` is now supported for NVC, GHDL, Icarus, Verilator, and Dsim using an external waveform viewer, displaying the results after the simulation has ended. cocotb will start Surfer or GTKWave, in that order, if they are in the system path. Use ``COCOTB_WAVEFORM_VIEWER`` to specify viewer. (:pr:`4635`)
- Added a Python type checker (`mypy <https://mypy.readthedocs.io/en/stable/getting_started.html>`_) to CI to ensure type correctness. (:pr:`4672`)
- Allow user to specify iverilog wave dump file location at run time with a plusarg. (:pr:`4721`)
- Added :envvar:`COCOTB_REWRITE_ASSERTION_FILES` to allow users to select which files to enable ``pytest``'s assertion rewriting in, or disable it. (:pr:`4728`)
- Added :func:`cocotb.task.current_task` to get the current task object. (:pr:`4730`)
- Added the ``name`` keyword argument to :func:`cocotb.start_soon`, :func:`cocotb.start`, and :func:`cocotb.create_task` to set a :class:`.Task`\ s name during creation. (:pr:`4777`)
- Added :meth:`.Task.get_name` and :meth:`.Task.set_name` to get and set a :class:`.Task`\ s name. (:pr:`4777`)


Bugfixes
--------

- Fixes handling of escaped identifiers containing characters that are special in regular expressions (e.g. dots). (:pr:`1610`)
- Updated :meth:`.ValueObjectBase.setimmediatevalue` to use ``GPI_NO_DELAY`` to set values, so values are *actually* set immediately and can be read back immediately. (:pr:`4068`)
- Support reading and writing all possible 9-state values in VHDL; ``W``, ``H``, and ``L`` were missing before. (Note that GHDL only supports 4-state values.) (:pr:`4299`)
- Fixed several memory and callback leaks in the GPI. Simulations may use less memory and run slightly faster. (:pr:`4392`)
- Passing no triggers to :class:`~cocotb.triggers.First` previously hung the simulation indefinitely. Now, doing so raises a :exc:`ValueError` exception. (:pr:`4409`)
- Passing no triggers to :class:`~cocotb.triggers.Combine` previously hung the simulation indefinitely. Now, doing so makes ``Combine`` behave equivalently to :class:`~cocotb.triggers.NullTrigger`. (:pr:`4409`)
- Prevent multiple Tasks from sharing a :meth:`.Lock.acquire` Trigger. If this was shared it would cause all Tasks waiting on that same Trigger to think they have acquired the Lock. (:pr:`4473`)
- Passing :class:`~cocotb.handle.Force`, :class:`~cocotb.handle.Freeze`, :class:`~cocotb.handle.Release`, and :class:`~cocotb.handle.Immediate` to :meth:`handle.set() <cocotb.handle.ValueObjectBase.set>` and :attr:`handle.value <cocotb.handle.ValueObjectBase.value>` now applies the set immediately instead of applying it inertially. (:pr:`4479`)
- Fixed bug where scheduled writes at the end of a test are cancelled. (:pr:`4514`)
- Fixed a bug where :meth:`cancelling <cocotb.task.Task.cancel>` a Task that is awaiting a :class:`.First` or :class:`.Combine` doesn't cancel the underlying waiter Tasks, leading to lower performance or concealing test failures. (:pr:`4542`)
- Can no longer accidentally get :ref:`edge-triggers` on immutable signals that would indefinitely hang. (:pr:`4544`)
- Fixed issue with ``$dumpfile`` and ``$dumpvars`` not working on Verilator without also turning on global tracing. (:pr:`4591`)
- Support ``waves`` argument to :meth:`Runner.test() <cocotb_tools.runner.Runner.test>` for GHDL and NVC. (:pr:`4630`)
- Support ``timescale`` argument to :meth:`Runner.build() <cocotb_tools.runner.Runner.build>` and :meth:`Runner.test() <cocotb_tools.runner.Runner.test>` for DSim. (:pr:`4645`)
- Fix segfault when using VCS Slave Mode. (:pr:`4670`)
- Fixed bug where calling :meth:`.Event.wait` but not ``await``\ ing the returned Trigger, then calling :meth:`.Event.set`, then ``await``\ ing the Trigger would hang. (:pr:`4675`)


Deprecations and Removals
-------------------------

- Removed unmaintained WaveDrom support. Users (if any) are encouraged to include the code in their own codebase, or create a cocotb extension for it. (:pr:`2066`)
- Removed iteration (``for sub_handle in handle: ...``) and querying the length (``len(handle)``) of :class:`~cocotb.handle.IntegerObject`, :class:`~cocotb.handle.EnumObject`, and :class:`~cocotb.handle.RealObject`. (:pr:`2720`)
- Removed ``cocotb.handle.ConstantObject``. Use :attr:`.ValueObjectBase.is_const` to determine is an object is immutable instead. (:pr:`2720`)
- Deprecated :class:`int`, :class:`str`, and :class:`float` casts on :class:`simulator value objects <cocotb.handle.ValueObjectBase>`. Instead use the :attr:`.ValueObjectBase.value` getter, then cast the value. (:pr:`2720`)
- Removed the ``cocotb.decorators.public`` decorator. (:pr:`3251`)
- The deprecated :external+cocotb19:func:`cocotb.fork()` function was removed. (:pr:`3425`)
- Support for generator-based coroutines, which used the ``cocotb.coroutine`` decorator and :keyword:`yield` syntax, has been removed. To update to the new syntax, remove all uses of the decorator and convert the function to a :term:`coroutine function` using the :keyword:`async` and :keyword:`await` syntax. (:pr:`3509`)
- Removed the ``cocotb.memdebug`` module. (:pr:`3543`)
- :external+cocotb19:class:`cocotb.utils.lazy_property` was removed. Use :func:`functools.cached_property` instead. (:pr:`3547`)
- Removed ``cocotb.clock.BaseClock``. (:pr:`3550`)
- The ``prefix`` and ``postfix`` arguments to :meth:`TestFactory.generate_tests() <cocotb.regression.TestFactory.generate_tests>` are deprecated in favor of the more flexible ``name`` argument. (:pr:`3578`)
- Methods :external+cocotb19:meth:`~cocotb.simulator.gpi_sim_hdl.get_definition_name()` and :external+cocotb19:meth:`~cocotb.simulator.gpi_sim_hdl.get_definition_file()` of :class:`cocotb.handle.SimHandleBase` were removed in favor of :meth:`~cocotb.handle.SimHandleBase._def_name` and :meth:`~cocotb.handle.SimHandleBase._def_file`, respectively. (:pr:`3609`)
- ``cocotb.binary.BinaryValue``, ``cocotb.binary.BinaryRepresentation``, and the ``cocotb.binary`` module have been removed in favor of :class:`~cocotb.types.LogicArray`. (:pr:`3634`)
- Deprecated :external+cocotb19:envvar:`MODULE`, :external+cocotb19:envvar:`TOPLEVEL`, :external+cocotb19:envvar:`TESTCASE`, :external+cocotb19:envvar:`COVERAGE`, :external+cocotb19:make:var:`PLUSARGS`, and :external+cocotb19:envvar:`RANDOM_SEED`, that are respectively replaced with :envvar:`COCOTB_TEST_MODULES`, :envvar:`COCOTB_TOPLEVEL`, :envvar:`COCOTB_TESTCASE`, :envvar:`COCOTB_USER_COVERAGE`, :envvar:`COCOTB_PLUSARGS` and :envvar:`COCOTB_RANDOM_SEED` to avoid issues with simulators overwriting cocotb environment variables. (:pr:`3644`)
- :meth:`HierarchyObject._id() <cocotb.handle.HierarchyObject._id>` is now deprecated. Use ``handle["sub_handle_name"]`` syntax instead. (:pr:`3655`)
- The module ``cocotb.outcomes`` was made private. (:pr:`3672`)
- The module ``cocotb.xunit_reporter`` was made private. (:pr:`3672`)
- ``cocotb.types.concat`` was removed. Use ``Array(itertools.chain(a, b))`` instead. (:pr:`3705`)
- :class:`~cocotb.regression.TestFactory` is now deprecated. Use :class:`cocotb.parametrize` instead. (:pr:`3717`)
- ``cocotb.handle.ModifiableObject`` was removed along with its non-functional ``drivers()`` and ``loads()`` methods. (:pr:`3733`)
- Removed :attr:`cocotb.argc`. Use ``len(cocotb.argv)`` instead. (:pr:`3779`)
- ``cocotb.LANGUAGE`` was removed, use ``os.environ["TOPLEVEL_LANG"]`` if you need that information. (:pr:`3779`)
- :attr:`LogicArray.signed_integer <cocotb.types.LogicArray.signed_integer>` has been deprecated. Use :meth:`LogicArray.to_signed() <cocotb.types.LogicArray.to_signed>` instead. (:pr:`3792`)
- :attr:`LogicArray.binstr <cocotb.types.LogicArray.binstr>` has been deprecated. Use ``str(logic_array)`` instead. (:pr:`3792`)
- :attr:`LogicArray.integer <cocotb.types.LogicArray.integer>` has been deprecated. Use :meth:`LogicArray.to_unsigned() <cocotb.types.LogicArray.to_unsigned>` instead. (:pr:`3792`)
- The ``cocotb.scheduler`` module and ``cocotb.scheduler`` object have been made private. (:pr:`3806`)
- Deprecated the ``verilog_sources`` and ``vhdl_sources`` parameters to :meth:`Runner.build() <cocotb_tools.runner.Runner.build>`. Use the language-agnostic ``sources`` parameter instead. (:pr:`3836`)
- ``Event.fired`` attribute was made private. Use :meth:`.Event.is_set`. (:pr:`3851`)
- Removed ``cocotb.triggers.PythonTrigger``. Use ``not isinstance(trigger, cocotb.triggers.GPITrigger)`` instead. (:pr:`3851`)
- Made ``cocotb.triggers.Trigger.primed``, ``cocotb.triggers.GPITrigger.cbhdl``, and ``cocotb.triggers.Timer.sim_steps`` private. (:pr:`3851`)
- ``cocotb.result.TestComplete`` was removed. (:pr:`3864`)
- ``cocotb.result.ExternalException`` was removed. (:pr:`3864`)
- ``cocotb.triggers.Join.retval`` was removed. (:pr:`3931`)
- Support for passing ``0`` as the ``time`` argument to :class:`~cocotb.triggers.Timer` has been removed. If a rounding operation causes the value to become ``0``, we change it to 1 simulation time step. (:pr:`3937`)
- :attr:`LogicArray.buff <cocotb.types.LogicArray.buff>` has been deprecated. Use :meth:`.LogicArray.to_bytes` instead. (:pr:`3944`)
- The ``outcome`` parameter to :class:`~cocotb.triggers.NullTrigger` was removed. There is no alternative. (:pr:`3969`)
- Deprecated the undocumented ``data`` attribute on :class:`~cocotb.triggers.Event` and corresponding argument to :meth:`.Event.set`. (:pr:`3980`)
- Removed the ``cycles`` argument to :meth:`Clock.start() <cocotb.clock.Clock.start>`. Use :meth:`.Clock.stop` to stop the Clock at the desired time instead. (:pr:`3983`)
- ``cocotb.utils.want_color_output()``, ``cocotb.utils.remove_traceback_frames``, ``cocotb.utils.walk_coro_stack``, and ``cocotb.utils.extract_coro_stack`` were made private. (:pr:`4023`)
- The undocumented ``cocotb.triggers._TriggerException``, thrown when a trigger failed to register, was removed. :exc:`RuntimeError` is thrown in its place. (:pr:`4024`)
- :class:`~cocotb.task.Join` was deprecated, use the :class:`~cocotb.task.Task` being joined directly wherever ``Join(task)`` was previously used. (:pr:`4084`)
- :meth:`.Task.join` was deprecated, use the :class:`~cocotb.task.Task` being joined directly wherever ``task.join()`` was previously used. (:pr:`4084`)
- When constructing a :class:`~cocotb.types.LogicArray` from a :class:`int`, the ``range`` argument is now required. (:pr:`4093`)
- Constructing a :class:`~cocotb.types.LogicArray` from an :class:`int` now only accepts integer literals (unsigned). Use :meth:`.LogicArray.from_signed` to convert negative integers into :class:`~cocotb.types.LogicArray`\ s using two's complement representation. (:pr:`4093`)
- The module ``cocotb.decorators`` was removed. All functionality is now available directly in the ``cocotb`` namespace (e.g. ``cocotb.decorators.test`` is now :func:`cocotb.test`). (:pr:`4129`)
- Removed ``Task.has_started()``. (:pr:`4149`)
- Removed ``cocotb.utils.ParametrizedSingleton``. (:pr:`4382`)
- :class:`~cocotb.triggers.Edge` has been deprecated in favor of the new name :class:`~cocotb.triggers.ValueChange`. (:pr:`4382`)
- The attribute ``frequency`` on :class:`~cocotb.clock.Clock` was removed. (:pr:`4396`)
- :func:`cocotb.start` is deprecated in favor of :func:`cocotb.start_soon`. Follow the call to :func:`cocotb.start_soon` with an :class:`await NullTrigger() <cocotb.triggers.NullTrigger>` if you need the scheduled Task to run before continuing the current Task. (:pr:`4397`)
- :any:`cocotb.logging.SimLog` is deprecated. Use ``logging.getLogger(f"{name}.0x{ident:x}")`` instead. (:pr:`4423`)
- The attributes ``cocotb.handle.SimHandleBase._log``, ``cocotb.task.Task.log``, ``cocotb.clock.Clock.log``, and ``cocotb.triggers.Trigger.log`` have been made private. Users are encouraged to make their own loggers that aren't in the ``"cocotb"`` namespace. (:pr:`4467`)
- :class:`.TestSuccess` was deprecated. Use :func:`cocotb.pass_test` instead. (:pr:`4477`)
- :meth:`handle.setimmediatevalue() <cocotb.handle.ValueObjectBase.setimmediatevalue>` is deprecated. Use :meth:`handle.set(value, Action.NO_DELAY) <cocotb.handle.ValueObjectBase.set>` instead. (:pr:`4479`)
- Removed the undocumented ``__name__`` and ``__qualname__`` attributes from :class:`.Task`. (:pr:`4524`)
- ``cocotb.handle.RegionObject`` and ``cocotb.handle.NonHierarchyObject`` have been removed. (:pr:`4541`)
- Deprecated :attr:`.Event.name` and passing a ``name`` argument to :class:`.Event` constructors. (:pr:`4561`)
- :meth:`.Task.kill` is deprecated in favor of :meth:`.Task.cancel`. (:pr:`4573`)
- :class:`.Range`, :class:`.Logic`, :class:`.LogicArray`, and :class:`.Array` are now only available from the :mod:`cocotb.types` module. Their implementation modules are now private. (:pr:`4623`)
- ``cocotb.handle.SimHandle`` was made private. Generally, :class:`dut.hierarchy["path/to/thing"] <cocotb.handle.HierarchyObject>` or :meth:`.HierarchyObject._get` can be used get objects by a full path, which was the typical public use for this function originally. (:pr:`4623`)
- ``cocotb.regression_manager``, the global :class:`.RegressionManager` singleton, is now private. (:pr:`4623`)
- Deprecated :attr:`.Lock.name` and passing a ``name`` argument to :class:`.Lock` constructors. (:pr:`4723`)
- Removed ``cocotb.logging.SimBaseLog`` as the class no longer did anything. (:pr:`4775`)


Changes
-------

- When casting a :class:`simulator object <cocotb.handle.SimHandleBase>` to a :class:`str` return the :func:`repr` of the object instead of the :meth:`path <cocotb.handle.SimHandleBase._path>`. (:pr:`2720`)
- Testing equality of :class:`simulator value objects <cocotb.handle.ValueObjectBase>` now does identity equality instead of a value equality. Use ``handle.value == other_handle.value`` for the old behavior. (:pr:`2720`)
- Constant value objects are now returned as their corresponding :class:`simulator value object <cocotb.handle.ValueObjectBase>` subtype (e.g. integers in VHDL and Verilog are now :class:`~cocotb.handle.IntegerObject`\ s) instead of ``cocotb.handle.ConstantObject``. (:pr:`2720`)
- cocotb-bus can no longer be installed at the same time as cocotb using ``pip install cocotb[bus]``. Use ``pip install cocotb-bus`` instead. (:pr:`3436`)
- :func:`.resume` and :func:`.bridge` are now implemented as decorator functions and not types. All attributes, e.g. ``log``, are no longer available. (:pr:`3461`)
- Use of the :envvar:`COCOTB_TESTCASE` variable has been changed so that each element of :envvar:`COCOTB_TESTCASE` will now select all tests with a matching name across all :envvar:`COCOTB_TEST_MODULES`\ s instead of just the first one found. (:pr:`3578`)
- Getting a value with :attr:`.LogicArrayObject.value` now returns a :class:`~cocotb.types.LogicArray` instead of a ``cocotb.binary.BinaryValue``. (:pr:`3634`)
- The module ``cocotb.log`` was renamed to :mod:`cocotb.logging` to prevent clashing with :attr:`cocotb.log`. (:pr:`3673`)
- Moved ``cocotb.config`` to ``cocotb_tools.config`` and ``cocotb.runner`` to ``cocotb_tools.runner`` to improve startup speed. (:pr:`3731`)
- Getting a value with :attr:`.ArrayObject.value` now returns an :class:`~cocotb.types.Array` with the appropriate :class:`~cocotb.types.Range` set instead of a :class:`list`. This will change how the object is indexed to match the range of the simulation object, instead of ``0`` to ``len(handle)-1`` like before. (:pr:`3733`)
- Renamed ``cocotb.handle.NonConstantObject`` to :class:`~cocotb.handle.ValueObjectBase`. (:pr:`3733`)
- Renamed ``cocotb.handle.NonHierarchyIndexableObject`` to :class:`~cocotb.handle.ArrayObject`. (:pr:`3733`)
- Improved VHPI implementation of :func:`cocotb.simulator.get_root_handle`. The ``name`` parameter is now used for handle lookup only as the last fallback, after checking it against the name of the ``vhpiRootInst`` object and its associated ``entity`` object. Handle lookup by name now always includes the ``:`` prefix so that it matches the ``FullName`` of the instantiated object, and will not match objects in the library information model. (:pr:`3774`)
- :meth:`.Lock.locked` is now a method instead of an attribute. (:pr:`3851`)
- The base class for :ref:`Python runners <howto-python-runner>` has been renamed from ``Simulator`` to :class:`~cocotb_tools.runner.Runner`. (:pr:`4025`)
- Moved :class:`~cocotb.triggers.SimTimeoutError` from ``cocotb.result`` to :mod:`cocotb.triggers`. (:pr:`4039`)
- ``cocotb.ipython_support`` was moved to :mod:`cocotb_tools.ipython_support`. (:pr:`4053`)
- ``cocotb.external`` and ``cocotb.function`` have been renamed to :func:`cocotb.task.bridge` and :func:`cocotb.task.resume` to better reflect their intended use case. (:pr:`4054`)
- Writes performed following an :keyword:`await` on :class:`~cocotb.triggers.ReadWrite` will be applied immediately (but inertially) and not scheduled for the next ``ReadWrite``. (:pr:`4115`)
- Attempting to await on either the :class:`~cocotb.triggers.ReadWrite` or :class:`~cocotb.triggers.ReadOnly` trigger while in the ReadOnly phase, which is an illegal transition, now raises a :exc:`RuntimeError`. (:pr:`4208`)
- The GPI ``get_range`` method now returns a range's direction in addition to the left and right bounds. When using VHDL, the direction is set explicitly by the ``to``/``downto`` keywords in the range definition; otherwise, the direction is inferred by the relative values of the left and right bounds. This change also allows null range sizes to be inferred correctly in VHDL. (:pr:`4212`)
- Python interpreter embedding is now more robust when using Python 3.8+. Setting ``PYTHONHOME`` is no longer required, so simulator usage of Python scripts should no longer fail. (:pr:`4293`)
- ``bool`` casts of :class:`cocotb.handle.SimHandleBase` subclasses will now fail, to prevent silent failures caused by the change in behavior to ``bool(handle)``. Instead use ``None`` to represent a lack of handle and ``handle is not None`` instead of the bool cast. (:pr:`4296`)
- PyGPI user modules specified by :envvar:`PYGPI_USERS` no longer require the module-level definition of the function ``_sim_event``. Instead call ``cocotb.simulator.set_sim_event_callback`` if you need this functionality. (:pr:`4310`)
- PyGPI user modules specified by :envvar:`PYGPI_USERS` no longer require the module-level definition of functions ``_log_from_c`` and ``_filter_from_c``. Instead call ``cocotb.simulator.initialize_logger`` if you need this functionality. (:pr:`4310`)
- ``std_ulogic_vector``/``std_logic_vector`` signals and constants in VHDL and packed arrays of ``logic`` signals and parameters in Verilog are now discovered as :class:`.LogicArrayObject`\ s instead of ``cocotb.handle.ModifiableObject``. (:pr:`2720`) (:pr:`4318`)
- ``std_ulogic``/``std_logic`` signals and constants in VHDL and scalar ``logic`` signals and parameters in Verilog are now discovered as :class:`.LogicObject`\ s instead of ``cocotb.handle.ModifiableObject``. (:pr:`2720`) (:pr:`4318`)
- :exc:`KeyboardInterrupt` and :exc:`SystemExit` now end the simulation immediately. (:pr:`4330`)
- The Makefile test flow now fails the ``sim`` target if there are test failures. (:pr:`4337`)
- :attr:`.Clock.period` was changed to be in terms of the passed-in unit rather than simulation steps. (:pr:`4396`)
- The ``units`` argument was renamed to ``unit`` in :class:`~cocotb.clock.Clock`, :class:`~cocotb.triggers.Timer`, :func:`~cocotb.utils.get_sim_time`, :func:`~cocotb.utils.get_time_from_sim_steps`, and :func:`~cocotb.utils.get_sim_steps`. (:pr:`4455`)
- Log test failures at log level :data:`logging.WARNING`. (:pr:`4463`)
- :data:`cocotb.log` was previous the base ``"cocotb"`` Logger, but is now a Logger in the ``"test"`` namespace. It still defaults to the :data:`logging.INFO` log level. (:pr:`4467`)
- :envvar:`COCOTB_LOG_LEVEL` no longer sets the GPI loggers log level if supplied; use :envvar:`GPI_LOG_LEVEL` to do that. (:pr:`4467`)
- ``VPI_CHECKING`` and ``VHPI_CHECKING`` are removed and interface issues are now always emitted with a log level of :data:`logging.DEBUG`. (:pr:`4510`)
- ``PYGPI_ENTRY_POINT`` renamed to :envvar:`PYGPI_USERS`. (:pr:`4513`)
- :meth:`.Task.cancel` now causes a :exc:`~asyncio.CancelledError` to be thrown into the coroutine. This behavior is *scheduled*, so Tasks will not become cancelled immediately. (:pr:`4524`)
- Setting values too large for :class:`~cocotb.handle.IntegerObject`, :class:`~cocotb.handle.EnumObject`, and :class:`~cocotb.handle.LogicArrayObject` now raises :exc:`ValueError` instead of :exc:`OverflowError`. (:pr:`4543`)
- :class:`.Join` was moved from :mod:`cocotb.triggers` to :mod:`cocotb.task`. (:pr:`4544`)
- :class:`bool(Logic) <cocotb.types.Logic>` casts now treat ``H`` as ``True`` and ``L`` as ``False`` instead of raising :exc:`ValueError`. (:pr:`4551`)
- :meth:`.LogicArray.is_resolvable` now returns ``True`` for arrays containing ``H`` and ``L`` values. (:pr:`4551`)
- :class:`int(Logic) <cocotb.types.Logic>` casts now treat ``H`` as ``1`` and ``L`` as ``0`` instead of raising :exc:`ValueError`. (:pr:`4551`)
- Renamed ``cocotb.types.ArrayLike`` to :class:`.AbstractArray`. (:pr:`4623`)
- The minimum supported version of Verilator has been increased to v5.036. (:pr:`4644`)
- If the user requests coverage collection via ``COCOTB_LIBRARY_COVERAGE`` or :envvar:`COCOTB_USER_COVERAGE` and the :mod:`coverage` module is not available, the regression will fail. (:pr:`4656`)
- Moved :class:`~cocotb.regression.SimFailure` from :mod:`cocotb.result` to :mod:`cocotb.regression`. (:pr:`4685`)


cocotb 1.9.2 (2024-10-26)
=========================

Bugfixes
--------

- Better handle errors happening during the startup phase.
- Fix toplevel discovery in Questa and Modelsim.

Features
--------

- Python 3.13 is now supported.

Deprecations and Removals
-------------------------

- The ``RTL_LIBRARY`` and :envvar:`TOPLEVEL_LIBRARY` Makefile variables were merged into :envvar:`TOPLEVEL_LIBRARY`. Update all uses of ``RTL_LIBRARY``.


cocotb 1.9.1 (2024-08-29)
=========================

Bugfixes
--------

- Improve the Verilator Makefile to pass on ``--trace`` at runtime as well. (:issue:`4088`)
- Pass :external+cocotb19:make:var:`EXTRA_ARGS` in the Verilator Makefile to both the compilation and the simulation step.

Changes
-------

- Support setuptools 72.2.0

cocotb 1.9.0 (2024-07-14)
=========================

Features
--------

- Not using parentheses on the :external+cocotb19:exc:`@cocotb.test <cocotb.test>` decorator is now supported. (:pr:`2731`)
- The :external+cocotb19:meth:`cocotb.runner.Simulator.build` method now accepts a ``clean`` argument to remove ``build_dir`` completely during build stage. (:pr:`3351`)
- Added support for the `NVC <https://github.com/nickg/nvc>`_ VHDL simulator. (:pr:`3427`)
- Added :external+cocotb19:make:var:`SIM_CMD_SUFFIX` to allow users to redirect simulator output or otherwise suffix the simulation command invocation. (:pr:`3561`)
- Added ``--trace`` command line argument to Verilator simulation binaries for run-time trace generation. This new argument is passed to the binary when the ``waves`` argument to :external+cocotb19:meth:`cocotb.runner.Simulator.test` is ``True``. (:pr:`3667`)
- The :external+cocotb19:meth:`cocotb.runner.Simulator.build` and :external+cocotb19:meth:`cocotb.runner.Simulator.test` methods now accept a ``log_file`` argument to redirect stdout and stderr to the specified file. (:pr:`3668`)
- The ``results_xml`` argument to :external+cocotb19:meth:`cocotb.runner.Simulator.test` can now be an absolute path. (:pr:`3669`)
- Added ``--trace-file`` command line argument to Verilator simulation binaries which specifies the trace file name. This can be passed to the binary by using the ``test_args`` argument to :external+cocotb19:meth:`cocotb.runner.Simulator.test`. (:pr:`3683`)
- The :external+cocotb19:meth:`cocotb.runner.Simulator.test` method now accepts a ``pre_cmd`` argument to run given commands before the simulation starts. These are typically Tcl commands for simulators that support them. Only support for the Questa simulator has been implemented. (:pr:`3744`)
- The ``sources`` option was added to :external+cocotb19:meth:`cocotb.runner.Simulator.build` to better support building mixed-language designs. (:pr:`3796`)
- Enable use of VPI fallback in all simulators when attempting to access generate blocks directly via lookup. This enables better support for simulators that don't support ``vpiGenScopeArray``, allowing discovery of generate blocks without having to iterate over the parent handle. (:pr:`3817`)
- Added support for comparing :external+cocotb19:class:`~cocotb.binary.BinaryValue` with :external+cocotb19:class:`~cocotb.types.Logic`, :external+cocotb19:class:`~cocotb.types.LogicArray`, and :class:`str`. (:pr:`3845`)
- Riviera-PRO now supports compilation into (multiple) VHDL libraries using :make:var:`VHDL_SOURCES_\<lib\>`. (:pr:`3922`)


Bugfixes
--------

- Xcelium 23.09.004 and newer can now be used to test designs with a VHDL toplevel. (:pr:`1076`)
- Fixed a potential issue where pseudo-region lookup may find the wrong generate block if the name of one generate block starts with the name of another generate block. (:pr:`2255`)
- Support ``waves`` argument to :external+cocotb19:meth:`cocotb.runner.Simulator.build` for Verilator. (:pr:`3681`)
- The ``test_args`` argument to :external+cocotb19:meth:`cocotb.runner.Simulator.test` is now passed to the Verilator simulation binary when running the simulation, which was previously missing. (:pr:`3682`)


Deprecations and Removals
-------------------------

- ``bool(Lock())`` is deprecated. Use :external+cocotb19:meth:`~cocotb.triggers.Lock.locked` instead. (:pr:`3871`)
- :external+cocotb19:attr:`cocotb.triggers.Join.retval` is deprecated. Use :external+cocotb19:meth:`cocotb.task.Task.result` to get the result of a finished Task. (:pr:`3871`)
- Passing the ``outcome`` argument to :class:`!NullTrigger` - which allowed the user to inject arbitrary outcomes when the trigger was :keyword:`await`\ ed - is deprecated. There is no alternative. (:pr:`3871`)
- :attr:`!Event.fired` is deprecated. Use :external+cocotb19:meth:`~cocotb.triggers.Event.is_set` instead. (:pr:`3871`)


Changes
-------

- For Aldec simulators, the ``-dbg`` and ``-O2`` options are no longer passed by default, as they reduce simulation speed. Pass these options in :external+cocotb19:make:var:`COMPILE_ARGS` and :external+cocotb19:make:var:`SIM_ARGS` if you need them for increased observability. (:pr:`3490`)
- :keyword:`await`\ ing a :external+cocotb19:class:`~cocotb.triggers.Join` trigger will yield the Join trigger and not the result of the task in the 2.0 release. (:pr:`3871`)
- :external+cocotb19:meth:`Lock.locked <cocotb.triggers.Lock.locked>` is now a method rather than an attribute to mirror :meth:`asyncio.Lock.locked`. (:pr:`3871`)


cocotb 1.8.1 (2023-10-06)
=========================

Features
--------

- Python 3.12 is now supported. (:issue:`3409`)

Bugfixes
--------

- Fix incorrect cleanup of pending Tasks (queued by :external+cocotb18:func:`cocotb.start_soon` but not started yet) when a test ends. (:issue:`3354`)


cocotb 1.8.0 (2023-06-15)
=========================

Features
--------

- :external+cocotb18:class:`cocotb.types.LogicArray` now supports a default value construction if a :external+cocotb19:class:`~cocotb.types.Range` is given. (:pr:`3031`)
- Add support for :class:`fractions.Fraction` and :class:`decimal.Decimal` to the ``period`` argument of :external+cocotb18:class:`cocotb.clock.Clock`. (:pr:`3045`)
- This release adds the :external+cocotb18:ref:`Python Test Runner <howto-python-runner>`, an experimental replacement for the traditional Makefile-based build and run flow. (:pr:`3103`)
- Incisive now supports compilation into a named VHDL library ``lib`` using ``VHDL_SOURCES_<lib>``. (:pr:`3261`)
- Cocotb can now correctly drive Verilator when its new ``--timing`` flag is used. (:pr:`3316`)
- Creating an FST waveform dump in Icarus Verilog can now be done by setting the :external+cocotb18:make:var:`WAVES` environment variable. Icarus-specific Verilog code is no longer required. (:pr:`3324`)


Bugfixes
--------

- Fixed Verilator not writing coverage files in some cases. (:pr:`1478`)
- The :external+cocotb18:data:`Regression Manager <cocotb.regression_manager>` now correctly handles exceptions raised in tests when the exceptions inherit from `BaseException`. (:pr:`3196`)
- Fix a performance regression when using Questa with FLI introduced in cocotb 1.7.0. (:pr:`3229`)
- Adds support for packed union in SystemVerilog when using Cadence Xcelium. (:pr:`3239`)
- Fixed :class:`RecursionError` caused by certain corner cases in the scheduler. (:pr:`3267`)
- Fixed cleanup in scheduler which caused sporadic warning messages and bugs in some corner cases. (:pr:`3270`)
- Fix "use after free" bug in VHPI implementation causing Riviera to fail to discover some simulation objects. (:pr:`3307`)


Changes
-------

- Removed ``level`` arg from ``_sim_event`` function in the :external+cocotb18:envvar:`PYGPI_ENTRY_POINT` interface. This function can only indicate a request to shutdown from the simulator or GPI. (:pr:`3066`)
- Moved :external+cocotb18:class:`cocotb.task.Task` and friends to ``cocotb.task`` module to alleviate internal cyclic import dependency. Users should update imports of the :class:`!Task` to import from the top-level :mod:`!cocotb` namespace. (:pr:`3067`)
- Added support for :external+cocotb18:make:var:`VERILOG_INCLUDE_DIRS` in the Makefiles. (:pr:`3189`)
- Changed platform support: Added Red Hat Enterprise Linux 9 (RHEL) and compatible clones, added macOS 13 x86_64 (Ventura on Intel), removed Ubuntu 18.04 (end-of-life). Note that Python wheels compatible with Ubuntu 18.04 remain available for the time being. Even though the cocotb project does not provide pre-compiled binaries for unsupported platforms users can typically compile cocotb themselves, as done automatically when running ``pip install``.

cocotb 1.7.2 (2022-11-15)
=========================

Changes
-------
- Python 3.11 is now supported.
- ``find_libpython``, a library to find (as the name indicates) libpython, is now a dependency of cocotb.
  Its latest version resolves an issue for users on RedHat Enterprise Linux (RHEL) 8 and Python 3.8, where the correct Python library would not be detected. (:issue:`3097`)

Bugfixes
--------

- Fixed a segmentation fault in Aldec Riviera-PRO that prevented mixed-language simulation from running. (:issue:`3078`)

cocotb 1.7.1 (2022-09-17)
=========================

Bugfixes
--------

- Fixed the packaging of the source distribution (sdist) to include all necessary files. (:pr:`3072`)
- Documented the fact that ``libstdc++-static`` needs to be available on some Linux distributions to install cocotb from source. (:pr:`3082`)

cocotb 1.7.0 (2022-09-06)
=========================

Features
--------

- Removed the need for ModelSim or Questa being installed when building cocotb. Similar to the approach taken with VPI and VHPI, cocotb now includes all C header files to build the FLI interface. This improvement was done in close collaboration with Siemens EDA, who changed the license of the relevant source code file. (:pr:`2948`)
- With Questa 2022.3 VHPI support is now fully working and no longer experimental. cocotb still defaults to using the FLI interface for VHDL toplevels with Questa. Users can choose VHPI instead by setting the :external+cocotb17:make:var:`VHDL_GPI_INTERFACE` environment variable to ``vhpi`` before running cocotb. (:pr:`2803`)
- cocotb tests are now more reproducible. (:pr:`2721`)
- :external+cocotb17:class:`~cocotb.handle.Force`, :external+cocotb17:class:`~cocotb.handle.Freeze`, and :external+cocotb17:class:`~cocotb.handle.Release` are now supported when using the FLI, Questa's traditional method to access VHDL. (:pr:`2775`)
- cocotb binaries now statically link libstdc++ on Linux, which prevents library load errors even if the simulator ships its own libstdc++. (:pr:`3002`)


Bugfixes
--------

- Fixed write scheduling to apply writes oldest to newest. (:pr:`2792`)
- Fixed Riviera makefile error for mixed-language simulation when VHDL is the top-level. This bug prevented the VPI library from loading correctly, and was a regression in 1.5.0. (:pr:`2912`)
- Fixed FLI issue where unprimed triggers were still firing. (:pr:`3010`)


Deprecations and Removals
-------------------------

- :external+cocotb17:func:`cocotb.fork()` has been deprecated in favor of :external+cocotb17:func:`cocotb.start_soon` or :external+cocotb17:func:`cocotb.start`. (:pr:`2663`)


Changes
-------

- Passing :term:`python:coroutine`\ s to :external+cocotb17:func:`~cocotb.triggers.with_timeout` is now supported. (:pr:`2494`)
- Renamed ``RunningTask`` to :external+cocotb17:class:`~cocotb.decorators.Task`. (:pr:`2876`)
- Made :external+cocotb17:class:`~cocotb.decorators.Task` interface more like :class:`asyncio.Task`'s. (:pr:`2876`)
- When code coverage is enabled with :external+cocotb17:envvar:`COVERAGE` and a configuration file is specified with :envvar:`!COVERAGE_RCFILE`, default coverage configuration is not applied to avoid overriding the user-defined configuration. (:pr:`3014`)


cocotb 1.6.2 (2022-02-07)
=========================

Bugfixes
--------

- Fix regression in :external+cocotb16:class:`~cocotb.regression.TestFactory` when using generator-based test coroutines. (:issue:`2839`)

Changes
-------

- Change how :envvar:`PYTHONHOME` is populated to work with broken mingw environments. (:issue:`2739`)


cocotb 1.6.1 (2021-12-07)
=========================

Bugfixes
--------

- Fix regression in :external+cocotb16:class:`~cocotb.regression.TestFactory` wrt unique test names. (:issue:`2781`)

cocotb 1.6.0 (2021-10-20)
=========================

Features
--------

- Support a custom entry point from C to Python with :external+cocotb16:envvar:`PYGPI_ENTRY_POINT`. (:pr:`1225`)
- Added :external+cocotb16:class:`~cocotb.types.Logic` and ``cocotb.types.Bit`` modeling datatypes. (:pr:`2059`)
- ModelSim and Questa now support compilation into a named VHDL library ``lib`` using ``VHDL_SOURCES_<lib>``. (:pr:`2465`)
- Added the :external+cocotb16:class:`~cocotb.types.LogicArray` modeling datatype. (:pr:`2514`)
- Xcelium now supports compilation into a named VHDL library ``lib`` using ``VHDL_SOURCES_<lib>``. (:pr:`2614`)
- Add the :external+cocotb16:make:var:`SIM_CMD_PREFIX` to supported Makefile variables, allowing users to pass environment variables and other command prefixes to simulators. (:pr:`2615`)
- To support VHDL libraries in ModelSim/Questa/Xcelium, :external+cocotb16:make:var:`VHDL_LIB_ORDER` has been added to specify a library compilation order. (:pr:`2635`)
- :external+cocotb16:func:`cocotb.fork()`, :external+cocotb16:func:`cocotb.start`, :external+cocotb16:func:`cocotb.start_soon`, and :external+cocotb16:func:`cocotb.create_task` now accept any object that implements the :class:`collections.abc.Coroutine` protocol. (:pr:`2647`)
- :external+cocotb16:class:`~cocotb.regression.TestFactory` and :external+cocotb16:class:`cocotb.test` now accept any :class:`collections.abc.Callable` object which returns a :class:`collections.abc.Coroutine` as a test function. (:pr:`2647`)
- Added :external+cocotb16:func:`cocotb.start` and :external+cocotb16:func:`cocotb.start_soon` scheduling functions. (:pr:`2660`)
- Add :external+cocotb16:func:`cocotb.create_task` API for creating a Task from a Coroutine without scheduling. (:pr:`2665`)
- Support rounding modes in :external+cocotb16:class:`~cocotb.triggers.Timer`. (:pr:`2684`)
- Support rounding modes in :external+cocotb16:func:`~cocotb.utils.get_sim_steps`. (:pr:`2684`)
- Support passing ``'step'`` as a time unit in :external+cocotb16:func:`cocotb.utils.get_sim_time`. (:pr:`2691`)


Bugfixes
--------

- VHDL signals that are zero bits in width now read as the integer ``0``, instead of raising an exception. (:pr:`2294`)
- Correctly parse plusargs with ``=``\ s in the value. (:pr:`2483`)
- :external+cocotb16:envvar:`COCOTB_RESULTS_FILE` now properly communicates with the :external+cocotb16:data:`Regression Manager <cocotb.regression_manager>` to allow overloading the result filename. (:pr:`2487`)
- Fixed several scheduling issues related to the use of :external+cocotb16:func:`cocotb.start_soon`. (:pr:`2504`)
- Verilator and Icarus now support running without specifying a :external+cocotb16:envvar:`TOPLEVEL`. (:pr:`2547`)
- Fixed discovery of signals inside SystemVerilog interfaces. (:pr:`2683`)


Improved Documentation
----------------------

- The :external+cocotb16:doc:`analog_model` example has been added, showing how to use Python models for analog circuits together with a digital part. (:pr:`2438`)


Deprecations and Removals
-------------------------

- Setting values on indexed handles using the ``handle[i] = value`` syntax is deprecated. Instead use the ``handle[i].value = value`` syntax. (:pr:`2490`)
- Setting values on handles using the ``dut.handle = value`` syntax is deprecated. Instead use the ``handle.value = value`` syntax. (:pr:`2490`)
- Setting values on handles using the ``signal <= newval`` syntax is deprecated. Instead, use the ``signal.value = newval`` syntax. (:pr:`2681`)
- :external+cocotb16:func:`cocotb.utils.hexdump` is deprecated; use :func:`scapy.utils.hexdump` instead. (:pr:`2691`)
- :external+cocotb16:func:`cocotb.utils.hexdiffs` is deprecated; use :func:`scapy.utils.hexdiff` instead. (:pr:`2691`)
- Passing ``None`` to :external+cocotb16:func:`cocotb.utils.get_sim_time` is deprecated; use ``'step'`` as the time unit instead. (:pr:`2691`)
- The ``stdout`` and ``stderr`` attributes on :external+cocotb16:class:`cocotb.result.TestComplete` and subclasses are deprecated. (:pr:`2692`)
- ``TestFailure`` is deprecated, use an :keyword:`assert` statement instead. (:pr:`2692`)


Changes
-------

- Assigning out-of-range Python integers to signals will now raise an :exc:`OverflowError`. (:pr:`2316`)
- cocotb now requires Python 3.6+. (:pr:`2422`)
- Selecting tests using :external+cocotb16:envvar:`TESTCASE` will now search for the first occurrence of a test of that name in order of modules listed in :external+cocotb16:envvar:`MODULE`\ s, and not just the first module in that list. (:pr:`2434`)
- The environment variable :external+cocotb16:envvar:`COCOTB_LOG_LEVEL` now supports ``TRACE`` value, which is used for verbose low-level logging that was previously in ``DEBUG`` logs. (:pr:`2502`)
- Improves formatting on test-related logging outputs. (:pr:`2564`)
- Shorter log lines (configurable with :external+cocotb16:envvar:`COCOTB_REDUCED_LOG_FMT`) are now the default. For wider log output, similar to previous cocotb releases, set the :external+cocotb16:envvar:`COCOTB_REDUCED_LOG_FMT` environment variable to ``0``. (:pr:`2564`)


cocotb 1.5.2 (2021-05-03)
=========================

Bugfixes
--------

- Changed some makefile syntax to support GNU Make 3. (:pr:`2496`)
- Fixed behavior of ``cocotb-config --libpython`` when finding libpython fails. (:pr:`2522`)


cocotb 1.5.1 (2021-03-20)
=========================

Bugfixes
--------

- Prevent pytest assertion rewriting (:pr:`2028`) from capturing stdin, which causes problems with IPython support. (:pr:`1649`) (:pr:`2462`)
- Add dependency on `cocotb_bus <https://github.com/cocotb/cocotb-bus>`_ to prevent breaking users that were previously using the bus and testbenching objects. (:pr:`2477`)
- Add back functionality to ``cocotb.binary.BinaryValue`` that allows the user to change ``binaryRepresentation`` after object creation. (:pr:`2480`)


cocotb 1.5.0 (2021-03-11)
=========================

Features
--------

- Support for building with Microsoft Visual C++ has been added.
  See :external+cocotb15:ref:`install` for more details. (:pr:`1798`)
- Makefiles now automatically deduce :external+cocotb15:make:var:`TOPLEVEL_LANG` based on the value of :external+cocotb15:make:var:`VERILOG_SOURCES` and :external+cocotb15:make:var:`VHDL_SOURCES`.
  Makefiles also detect incorrect usage of :external+cocotb15:make:var:`TOPLEVEL_LANG` for simulators that only support one language. (:pr:`1982`)
- :external+cocotb15:func:`cocotb.fork()` will now raise a descriptive :class:`TypeError` if a coroutine function is passed into them. (:pr:`2006`)
- Added ``cocotb.scheduler.start_soon()`` which schedules a coroutine to start *after* the current coroutine yields control.
  This behavior is distinct from :external+cocotb15:func:`cocotb.fork()` which schedules the given coroutine immediately. (:pr:`2023`)
- If ``pytest`` is installed, its assertion-rewriting framework will be used to
  produce more informative tracebacks from the :keyword:`assert` statement. (:pr:`2028`)
- The handle to :external+cocotb15:envvar:`TOPLEVEL`, typically seen as the first argument to a cocotb test function, is now available globally as :external+cocotb15:data:`cocotb.top`. (:pr:`2134`)
- The ``units`` argument to :external+cocotb15:class:`~cocotb.triggers.Timer`,
  :external+cocotb15:class:`~cocotb.clock.Clock` and :external+cocotb15:func:`~cocotb.utils.get_sim_steps`,
  and the ``timeout_unit`` argument to
  :external+cocotb15:func:`~cocotb.triggers.with_timeout` and :external+cocotb15:class:`cocotb.test`
  now accepts ``'step'`` to mean the simulator time step.
  This used to be expressed using ``None``, which is now deprecated. (:pr:`2171`)
- :external+cocotb15:meth:`TestFactory.add_option() <cocotb.regression.TestFactory.add_option>` now supports groups of options when a full Cartesian product is not desired. (:pr:`2175`)
- Added asyncio-style queues, :external+cocotb15:class:`~cocotb.queue.Queue`, :external+cocotb15:class:`~cocotb.queue.PriorityQueue`, and :external+cocotb15:class:`~cocotb.queue.LifoQueue`. (:pr:`2297`)
- Support for the SystemVerilog type ``bit`` has been added. (:pr:`2322`)
- Added the ``--lib-dir``,  ``--lib-name`` and ``--lib-name-path`` options to the ``cocotb-config`` command to make cocotb integration into existing flows easier. (:pr:`2387`)
- Support for using Questa's VHPI has been added.
  Use :external+cocotb15:make:var:`VHDL_GPI_INTERFACE` to select between using the FLI or VHPI when dealing with VHDL simulations.
  Note that VHPI support in Questa is still experimental at this time. (:pr:`2408`)


Bugfixes
--------

- Assigning Python integers to signals greater than 32 bits wide will now work correctly for negative values. (:pr:`913`)
- Fix GHDL's library search path, allowing libraries other than ``work`` to be used in simulation. (:pr:`2038`)
- Tests skipped by default (created with `skip=True`) can again be run manually by setting the :external+cocotb15:envvar:`TESTCASE` variable. (:pr:`2045`)
- In :external+cocotb15:ref:`Icarus Verilog <sim-icarus>`, generate blocks are now accessible directly via lookup without having to iterate over parent handle. (:pr:`2079`, :pr:`2143`)

    .. code-block:: python

        # Example pseudo-region
        dut.genblk1       #<class 'cocotb.handle.HierarchyArrayObject'>

    .. consume the towncrier issue number on this line. (:pr:`2079`)
- Fixed an issue with VHPI on Mac OS and Linux where negative integers were returned as large positive values. (:pr:`2129`)


Improved Documentation
----------------------

- The  :external+cocotb15:ref:`mixed_signal` example has been added,
  showing how to use HDL helper modules in cocotb testbenches that exercise
  two mixed-signal (i.e. analog and digital) designs. (:pr:`1051`)
- New example :external+cocotb15:ref:`matrix_multiplier`. (:pr:`1502`)
- A :external+cocotb15:ref:`refcard` showing the most used features of cocotb has been added. (:pr:`2321`)
- A chapter :external+cocotb15:ref:`custom-flows` has been added. (:pr:`2340`)


Deprecations and Removals
-------------------------

- The contents of :external+cocotb15:mod:`cocotb.generators` have been deprecated. (:pr:`2047`)
- The outdated "Sorter" example has been removed from the documentation. (:pr:`2049`)
- Passing :class:`bool` values to ``expect_error`` option of :class:`cocotb.test` is deprecated.
  Pass a specific :class:`Exception` or a tuple of Exceptions instead. (:pr:`2117`)
- The system task overloads for ``$info``, ``$warn``, ``$error`` and ``$fatal`` in Verilog and mixed language testbenches have been removed. (:pr:`2133`)
- ``TestError`` has been deprecated, use :ref:`python:bltin-exceptions`. (:pr:`2177`)
- The undocumented class ``cocotb.xunit_reporter.File`` has been removed. (:pr:`2200`)
- Deprecated :external+cocotb15:class:`cocotb.hook` and :external+cocotb15:envvar:`COCOTB_HOOKS`.
  See the documentation for :external+cocotb15:class:`cocotb.hook` for suggestions on alternatives. (:pr:`2201`)
- Deprecate ``cocotb.utils.pack`` and ``cocotb.utils.unpack`` and the use of :class:`ctypes.Structure` in signal assignments. (:pr:`2203`)
- The outdated "ping" example has been removed from the documentation and repository. (:pr:`2232`)
- Using the undocumented custom format :class:`dict` object in signal assignments has been deprecated. (:pr:`2240`)
- The access modes of many interfaces in the cocotb core libraries were re-evaluated.
  Some interfaces that were previously public are now private and vice versa.
  Accessing the methods through their old name will create a :class:`DeprecationWarning`.
  In the future, the deprecated names will be removed. (:pr:`2278`)
- The bus and testbenching components in cocotb have been officially moved to the `cocotb-bus <https://github.com/cocotb/cocotb-bus>`_ package.
  This includes
  :class:`!cocotb.bus.Bus`,
  :class:`!cocotb.scoreboard.Scoreboard`,
  everything in :mod:`!cocotb.drivers`,
  and everything in :mod:`!cocotb.monitor`.
  Documentation will remain in the main cocotb repository for now.
  Old names will continue to exist, but their use will cause a :class:`DeprecationWarning`,
  and will be removed in the future. (:pr:`2289`)


Changes
-------

- Assigning negative Python integers to handles does an implicit two's compliment conversion. (:pr:`913`)
- Updated :external+cocotb15:class:`~cocotb_bus.drivers.Driver`, :external+cocotb15:class:`~cocotb_bus.monitors.Monitor`, and all their subclasses to use the :keyword:`async`/:keyword:`await` syntax instead of the :keyword:`yield` syntax. (:pr:`2022`)
- The package build process is now fully :pep:`517` compliant. (:pr:`2091`)
- Improved support and performance for :external+cocotb15:ref:`sim-verilator` (version 4.106 or later now required). (:pr:`2105`)
- Changed how libraries are specified in :external+cocotb15:envvar:`GPI_EXTRA` to allow specifying libraries with paths, and names that don't start with "lib". (:pr:`2341`)


cocotb 1.4.0 (2020-07-08)
=========================

Features
--------

- :external+cocotb14:class:`~cocotb.triggers.Lock` can now be used in :keyword:`async with` statements. (:pr:`1031`)
- Add support for distinguishing between ``net`` (``vpiNet``) and ``reg`` (``vpiReg``) type when using the VPI interface. (:pr:`1107`)
- Support for dropping into :mod:`pdb` upon failure, via the new :external+cocotb14:envvar:`COCOTB_PDB_ON_EXCEPTION` environment variable. (:pr:`1180`)
- Simulators run through a Tcl script (Aldec Riviera Pro and Mentor simulators) now support a new :external+cocotb14:make:var:`RUN_ARGS` Makefile variable, which is passed to the first invocation of the tool during runtime. (:pr:`1244`)
- Cocotb now supports the following example of forking a *non-decorated* :external+cocotb14:ref:`async coroutine <async_functions>`.

  .. code-block:: python

     async def example():
         for i in range(10):
             await cocotb.triggers.Timer(10, "ns")

     cocotb.fork(example())

  ..
     towncrier will append the issue number taken from the file name here:

  Issue (:pr:`1255`)
- The cocotb log configuration is now less intrusive, and only configures the root logger instance, ``logging.getLogger()``, as part of :external+cocotb14:func:`cocotb.log.default_config` (:pr:`1266`).

  As such, it is now possible to override the default cocotb logging behavior with something like::

      # remove the cocotb log handler and formatting
      root = logging.getLogger()
      for h in root.handlers[:]:
          root.remove_handler(h)
          h.close()

      # add your own
      logging.basicConfig()

  .. consume the towncrier issue number on this line. (:pr:`1266`)
- Support for ``vpiRealNet``. (:pr:`1282`)
- The colored output can now be disabled by the :external+cocotb14:envvar:`NO_COLOR` environment variable. (:pr:`1309`)
- Cocotb now supports deposit/force/release/freeze actions on simulator handles, exposing functionality similar to the respective Verilog/VHDL assignments.

  .. code-block:: python

     from cocotb.handle import Deposit, Force, Release, Freeze

     dut.q <= 1            # A regular value deposit
     dut.q <= Deposit(1)   # The same, higher verbosity
     dut.q <= Force(1)     # Force value of q to 1
     dut.q <= Release()    # Release q from a Force
     dut.q <= Freeze()     # Freeze the current value of q

  ..
     towncrier will append the issue number taken from the file name here:

  Issue (:pr:`1403`)
- Custom logging handlers can now access the simulator time using
  :external+cocotb14:attr:`logging.LogRecord.created_sim_time`, provided the
  :external+cocotb14:class:`~cocotb.log.SimTimeContextFilter` filter added by
  :external+cocotb14:func:`~cocotb.log.default_config` is not removed from the logger instance. (:pr:`1411`)
- Questa now supports :external+cocotb14:make:var:`PLUSARGS`.
  This requires that ``tcl.h`` be present on the system.
  This is likely included in your installation of Questa, otherwise, specify ``CFLAGS=-I/path/to/tcl/includedir``. (:pr:`1424`)
- The name of the entry point symbol for libraries in :external+cocotb14:envvar:`GPI_EXTRA` can now be customized.
  The delimiter between each library in the list has changed from ``:`` to ``,``. (:pr:`1457`)
- New methods for setting the value of a ``cocotb.handle.NonHierarchyIndexableObject`` (HDL arrays). (:pr:`1507`)

  .. code-block:: python

      # Now supported
      dut.some_array <= [0xAA, 0xBB, 0xCC]
      dut.some_array.value = [0xAA, 0xBB, 0xCC]

      # For simulators that support n-dimensional arrays
      dut.some_2d_array <= [[0xAA, 0xBB], [0xCC, 0xDD]]
      dut.some_2d_array.value = [[0xAA, 0xBB], [0xCC, 0xDD]]

  .. consume the towncrier issue number on this line. (:pr:`1507`)
- Added support for Aldec's Active-HDL simulator. (:pr:`1601`)
- Including ``Makefile.inc`` from user makefiles is now a no-op and deprecated. Lines like  ``include $(shell cocotb-config --makefiles)/Makefile.inc`` can be removed from user makefiles without loss in functionality. (:pr:`1629`)
- Support for using :keyword:`await` inside an embedded IPython terminal, using ``cocotb.ipython_support``. (:pr:`1649`)
- Added :external+cocotb14:meth:`~cocotb.triggers.Event.is_set`, so users may check if an :external+cocotb14:class:`~cocotb.triggers.Event` has fired. (:pr:`1723`)
- The :external+cocotb14:func:`cocotb.simulator.is_running` function was added so a user of cocotb could determine if they are running within a simulator. (:pr:`1843`)


Bugfixes
--------

- Tests which fail at initialization, for instance due to no ``yield`` being present, are no longer silently ignored. (:pr:`1253`)
- Tests that were not run because predecessors threw ``cocotb.result.SimFailure``, and caused the simulator to exit, are now recorded with an outcome of ``cocotb.result.SimFailure``.
  Previously, these tests were ignored. (:pr:`1279`)
- Makefiles now correctly fail if the simulation crashes before a ``results.xml`` file can be written. (:pr:`1314`)
- Logging of non-string messages with colored log output is now working. (:pr:`1410`)
- Getting and setting the value of a ``cocotb.handle.NonHierarchyIndexableObject`` now iterates through the correct range of the simulation object, so arrays that do not start/end at index 0 are supported. (:pr:`1507`)
- The :external+cocotb14:class:`~cocotb.monitors.xgmii.XGMII` monitor no longer crashes on Python 3, and now assembles packets as :class:`bytes` instead of :class:`str`. The :external+cocotb14:class:`~cocotb.drivers.xgmii.XGMII` driver has expected :class:`bytes` since cocotb 1.2.0. (:pr:`1545`)
- ``signal <= value_of_wrong_type`` no longer breaks the scheduler, and throws an error immediately. (:pr:`1661`)
- Scheduling behavior is now consistent before and after the first :keyword:`await` of a :external+cocotb14:class:`~cocotb.triggers.GPITrigger`. (:pr:`1705`)
- Iterating over ``for generate`` statements using VHPI has been fixed. This bug caused some simulators to crash, and was a regression in version 1.3. (:pr:`1882`)
- The :external+cocotb14:class:`~cocotb.drivers.xgmii.XGMII` driver no longer emits a corrupted word on the first transfer. (:pr:`1905`)


Improved Documentation
----------------------

- If a makefile uses cocotb's :file:`Makefile.sim`, ``make help`` now lists the supported targets and variables. (:pr:`1318`)
- A new section :external+cocotb14:ref:`rotating-logger` has been added. (:pr:`1400`)
- The documentation at http://docs.cocotb.org/ has been restructured,
  making it easier to find relevant information. (:pr:`1482`)


Deprecations and Removals
-------------------------

- ``cocotb.utils.reject_remaining_kwargs`` is deprecated, as it is no longer
  needed now that we only support Python 3.5 and newer. (:pr:`1339`)
- The value of :external+cocotb14:class:`cocotb.handle.StringObject`\ s is now of type :class:`bytes`, instead of  :class:`str` with an implied ASCII encoding scheme. (:pr:`1381`)
- ``ReturnValue`` is now deprecated. Use a :keyword:`return` statement instead; this works in all supported versions of Python. (:pr:`1489`)
- The makefile variable :make:var:`!VERILATOR_TRACE`
  that was not supported for all simulators has been deprecated.
  Using it prints a deprecation warning and points to the documentation section
  :external+cocotb14:ref:`simulator-support` explaining how to get the same effect by other means. (:pr:`1495`)
- ``cocotb.binary.BinaryValue.get_hex_buff`` produced nonsense and has been removed. (:pr:`1511`)
- Passing :class:`str` instances to ``cocotb.utils.hexdump`` and ``cocotb.utils.hexdiffs`` is deprecated. :class:`bytes` objects should be passed instead. (:pr:`1519`)
- ``Makefile.pylib``, which provided helpers for building C extension modules for Python, has been removed.
  Users of the ``PYTHON_LIBDIR`` and ``PYTHON_INCLUDEDIR`` variables will now have to compute these values themselves.
  See the ``endian_swapper`` example for how to do this. (:pr:`1632`)
- Makefile and documentation for the NVC simulator which has never worked have been removed. (:pr:`1693`)


Changes
-------

- Cocotb no longer supports Python 2, at least Python 3.5 is now required.
  Users of Python 2.7 can still use cocotb 1.3, but are heavily encouraged to update.
  It is recommended to use the latest release of Python 3 for improved performance over older Python 3 versions. (:pr:`767`)
- Mentor Questa, Aldec Riviera-PRO and GHDL are now started in the directory containing the Makefile and also save :file:`results.xml` there, bringing them in line with the behavior used by other simulators. (:pr:`1598`) (:pr:`1599`) (:pr:`1063`)
- Tests are now evaluated in order of their appearance in the :external+cocotb14:envvar:`MODULE` environment variable, their stage, and the order of invocation of the :external+cocotb14:class:`cocotb.test` decorator within a module. (:pr:`1380`)
- All libraries are compiled during installation to the ``cocotb/libs`` directory.
  The interface libraries ``libcocotbvpi`` and ``libcocotbvhpi`` have been renamed to have a ``_simulator_name`` postfix.
  The ``simulator`` module has moved to :external+cocotb14:mod:`cocotb.simulator`.
  The ``LD_LIBRARY_PATH`` environment variable no longer needs to be set by the makefiles, as the libraries now discover each other via ``RPATH`` settings. (:pr:`1425`)
- Cocotb must now be :external+cocotb14:ref:`installed <installation-via-pip>` before it can be used. (:pr:`1445`)
- ``cocotb.handle.NonHierarchyIndexableObject.value`` is now a list in left-to-right range order of the underlying simulation object.
  Previously the list was always ordered low-to-high. (:pr:`1507`)
- Various binary representations have changed type from :class:`str` to :class:`bytes`. These include:

  * ``cocotb.binary.BinaryValue.buff``, which as a consequence means ``cocotb.binary.BinaryValue.assign``, no longer accepts malformed ``10xz``-style :class:`str`\ s (which were treated as binary).
  * The objects produced by :func:`!cocotb.generators.byte`, which means that single bytes are represented by :class:`int` instead of 1-character :class:`str`\ s.
  * The packets produced by the :external+cocotb14:class:`~cocotb.drivers.avalon.AvalonSTPkts`.

  Code working with these objects may find it needs to switch from creating :class:`str` objects like ``"this"`` to :class:`bytes` objects like ``b"this"``.
  This change is a consequence of the move to Python 3. (:pr:`1514`)
- There's no longer any need to set the ``PYTHON_BIN`` makefile variable, the Python executable automatically matches the one cocotb was installed into. (:pr:`1574`)
- The :external+cocotb14:make:var:`SIM` setting for Aldec Riviera-PRO has changed from ``aldec`` to ``riviera``. (:pr:`1691`)
- Certain methods on the :external+cocotb14:mod:`cocotb.simulator` Python module now throw a :exc:`RuntimeError` when no simulator is present, making it safe to use :mod:`!cocotb` without a simulator present. (:pr:`1843`)
- Invalid values of the environment variable :external+cocotb14:envvar:`COCOTB_LOG_LEVEL` are no longer ignored.
  They now raise an exception with instructions how to fix the problem. (:pr:`1898`)


cocotb 1.3.2 (2020-07-08)
=========================

Notable changes and bug fixes
-----------------------------

- Iterating over ``for generate`` statements using VHPI has been fixed.
  This bug caused some simulators to crash, and was a regression in version 1.3.1. (:pr:`1882`)


cocotb 1.3.1 (2020-03-15)
=========================

Notable changes and bug fixes
-----------------------------
- The Makefiles for the Aldec Riviera and Cadence Incisive simulators have been fixed to use the correct name of the VHPI library (``libcocotbvhpi``).
  This bug prevented VHDL designs from being simulated, and was a regression in 1.3.0. (:pr:`1472`)

cocotb 1.3.0 (2020-01-08)
=========================

This will likely be the last release to support Python 2.7.

New features
------------

- Initial support for the Verilator simulator (version 4.020 and above).
  The integration of Verilator into cocotb is not yet as fast or as powerful as it is for other simulators.
  Please use the latest version of Verilator, and `report bugs <https://github.com/cocotb/cocotb/issues/new>`_ if you experience problems.
- New makefile variables :external+cocotb13:make:var:`COCOTB_HDL_TIMEUNIT` and :external+cocotb13:make:var:`COCOTB_HDL_TIMEPRECISION` for setting the default time unit and precision that should be assumed for simulation when not specified by modules in the design. (:pr:`1113`)
- New ``timeout_time`` and ``timeout_unit`` arguments to :external+cocotb13:class:`cocotb.test`, for adding test timeouts. (:pr:`1119`)
- :external+cocotb13:func:`~cocotb.triggers.with_timeout`, for a shorthand for waiting for a trigger with a timeout. (:pr:`1119`)
- The ``expect_error`` argument to :external+cocotb13:class:`cocotb.test` now accepts a specific exception type. (:pr:`1116`)
- New environment variable :external+cocotb13:envvar:`COCOTB_RESULTS_FILE`, to allow configuration of the xUnit XML output filename. (:pr:`1053`)
- A new ``bus_separator`` argument to :external+cocotb13:class:`cocotb.drivers.BusDriver`. (:pr:`1160`)
- A new ``start_high`` argument to :external+cocotb13:attr:`cocotb.clock.Clock.start`. (:pr:`1036`)
- A new :data:`!cocotb.__version__` constant, which contains the version number of the running cocotb. (:pr:`1196`)

Notable changes and bug fixes
-----------------------------

- ``DeprecationWarning``\ s are now shown in the output by default.
- Tracebacks are now preserved correctly for exceptions in Python 2.
  The tracebacks in all Python versions are now a little shorter.
- :external+cocotb13:class:`cocotb.external` and :external+cocotb13:class:`cocotb.function` now work more reliably and with fewer race conditions.
- A failing :keyword:`assert` will be considered a test failure. Previously, it was considered a test *error*.
- :external+cocotb13:meth:`~cocotb.handle.NonConstantObject.drivers` and :external+cocotb13:meth:`~cocotb.handle.NonConstantObject.loads` now also work correctly in Python 3.7 onwards.
- :external+cocotb13:class:`~cocotb.triggers.Timer` can now be used with :class:`decimal.Decimal` instances, allowing constructs like ``Timer(Decimal("1e-9"), units="sec")`` as an alternate spelling for ``Timer(100, units="us")``. (:pr:`1114`)
- Many (editorial) documentation improvements.

Deprecations
------------

- :external+cocotb13:func:`cocotb.result.raise_error` and :external+cocotb13:func:`cocotb.result.create_error` are deprecated in favor of using Python exceptions directly.
  :external+cocotb13:exc:`~cocotb.result.TestError` can still be used if the same exception type is desired. (:pr:`1109`)
- The ``AvalonSTPktsWithChannel`` type is deprecated.
  Use the ``report_channel`` argument to :external+cocotb13:class:`~cocotb.monitors.avalon.AvalonSTPkts` instead.
- The ``colour`` attribute of log objects like ``cocotb.log`` or ``some_coro.log`` is deprecated.
  Use ``cocotb.utils.want_color_output`` instead. (:pr:`1231`)

Other news
----------

- cocotb is now packaged for Fedora Linux and available as `python-cocotb <https://src.fedoraproject.org/rpms/python-cocotb>`_. (`Fedora bug #1747574 <https://bugzilla.redhat.com/show_bug.cgi?id=1747574>`_) (thanks Ben Rosser)


cocotb 1.2.0 (2019-07-24)
=========================

New features
------------

- cocotb is now built as Python package and installable through pip. (:pr:`517`, :pr:`799`, :pr:`800`, :pr:`803`, :pr:`805`)
- Support for :keyword:`async` functions and generators was added (Python 3 only). Please have a look at :external+cocotb12:ref:`async_functions` for an example how to use this new feature.
- VHDL block statements can be traversed. (:pr:`850`)
- Support for Python 3.7 was added.

Notable changes and bug fixes
-----------------------------

- The heart of cocotb, its scheduler, is now even more robust. Many small bugs, inconsistencies and unreliable behavior have been ironed out.
- Exceptions are now correctly propagated between coroutines, giving users the "natural" behavior they'd expect with exceptions. (:pr:`633`)
- The :meth:`!handle.setimmediatevalue` function now works for values larger than 32 bit. (:pr:`768`)
- The documentation was cleaned up, improved and extended in various places, making it more consistent and complete.
- Tab completion in newer versions of IPython is fixed. (:pr:`825`)
- Python 2.6 is officially not supported any more. cocotb supports Python 2.7 and Python 3.5+.
- The cocotb GitHub project moved from ``potentialventures/cocotb`` to ``cocotb/cocotb``.
  Redirects for old URLs are in place.

Deprecations
------------

- The `bits` argument to ``cocotb.binary.BinaryValue``, which is now called `n_bits`.
- The `logger` attribute of log objects like ``cocotb.log`` or ``some_coro.log``, which is now just an alias for ``self``.
- The ``cocotb.utils.get_python_integer_types`` function, which was intended to be private.

Known issues
------------

- Depending on your simulation, cocotb 1.2 might be roughly 20 percent slower than cocotb 1.1.
  Much of the work in this release cycle went into fixing correctness bugs in the scheduler, sometimes at the cost of performance.
  We are continuing to investigate this in issue :issue:`961`.
  Independent of the cocotb version, we recommend using the latest Python 3 version, which is shown to be significantly faster than previous Python 3 versions, and slightly faster than Python 2.7.

Please have a look at the `issue tracker <https://github.com/cocotb/cocotb/issues>`_ for more outstanding issues and contribution opportunities.


cocotb 1.1 (2019-01-24)
=======================

This release is the result of four years of work with too many bug fixes, improvements and refactorings to name them all.


cocotb 1.0 (2015-02-15)
=======================

New features
------------

- FLI support for ModelSim
- Mixed Language, Verilog and VHDL
- Windows
- 300% performance improvement with VHPI interface
- WaveDrom support for wave diagrams.


cocotb 0.4 (2014-02-25)
=======================

New features
------------

- Issue :issue:`101`: Implement Lock primitive to support mutex
- Issue :issue:`105`: Compatibility with Aldec Riviera-Pro
- Issue :issue:`109`: Combine multiple :file:`results.xml` into a single results file
- Issue :issue:`111`: XGMII drivers and monitors added
- Issue :issue:`113`: Add operators to ``BinaryValue`` class
- Issue :issue:`116`: Native VHDL support by implementing VHPI layer
- Issue :issue:`117`: Added AXI4-Lite Master BFM

Bugs fixed
----------

- Issue :issue:`100`: Functional bug in endian_swapper example RTL
- Issue :issue:`102`: Only 1 coroutine wakes up of multiple coroutines wait() on an Event
- Issue :issue:`114`: Fix build issues with Cadence IUS simulator

New examples
------------

- Issue :issue:`106`: TUN/TAP example using ping


cocotb 0.3 (2013-09-27)
=======================

This contains a raft of fixes and feature enhancements.


cocotb 0.2 (2013-07-19)
=======================

New features
------------

- Release 0.2 supports more simulators and increases robustness over 0.1.
- A centralized installation is now supported (see documentation) with supporting libraries build when the simulation is run for the first time.


cocotb 0.1 (2013-07-09)
=======================

- The first release of cocotb.
- Allows installation and running against Icarus, VCS, Aldec simulators.
