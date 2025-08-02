# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import functools
import inspect
import logging
import warnings
from itertools import product
from typing import (
    TYPE_CHECKING,
    Callable,
    Coroutine,
    Dict,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
    cast,
    overload,
)

from cocotb._base_triggers import Trigger
from cocotb._decorators import Test
from cocotb._typing import TimeUnit

if TYPE_CHECKING:
    from types import FrameType, FunctionType


class TestFactory:
    """Factory to automatically generate tests.

    Args:
        test_function: A Callable that returns the test Coroutine.
            Must take *dut* as the first argument.
        *args: Remaining arguments are passed directly to the test function.
            Note that these arguments are not varied. An argument that
            varies with each test must be a keyword argument to the
            test function.
        **kwargs: Remaining keyword arguments are passed directly to the test function.
            Note that these arguments are not varied. An argument that
            varies with each test must be a keyword argument to the
            test function.

    Assuming we have a common test function that will run a test. This test
    function will take keyword arguments (for example generators for each of
    the input interfaces) and generate tests that call the supplied function.

    This Factory allows us to generate sets of tests based on the different
    permutations of the possible arguments to the test function.

    For example, if we have a module that takes backpressure, has two configurable
    features where enabling ``feature_b`` requires ``feature_a`` to be active, and
    need to test against data generation routines ``gen_a`` and ``gen_b``:

    >>> tf = TestFactory(test_function=run_test)
    >>> tf.add_option(name="data_in", optionlist=[gen_a, gen_b])
    >>> tf.add_option("backpressure", [None, random_backpressure])
    >>> tf.add_option(
    ...     ("feature_a", "feature_b"), [(False, False), (True, False), (True, True)]
    ... )
    >>> tf.generate_tests()

    We would get the following tests:

        * ``gen_a`` with no backpressure and both features disabled
        * ``gen_a`` with no backpressure and only ``feature_a`` enabled
        * ``gen_a`` with no backpressure and both features enabled
        * ``gen_a`` with ``random_backpressure`` and both features disabled
        * ``gen_a`` with ``random_backpressure`` and only ``feature_a`` enabled
        * ``gen_a`` with ``random_backpressure`` and both features enabled
        * ``gen_b`` with no backpressure and both features disabled
        * ``gen_b`` with no backpressure and only ``feature_a`` enabled
        * ``gen_b`` with no backpressure and both features enabled
        * ``gen_b`` with ``random_backpressure`` and both features disabled
        * ``gen_b`` with ``random_backpressure`` and only ``feature_a`` enabled
        * ``gen_b`` with ``random_backpressure`` and both features enabled

    The tests are appended to the calling module for auto-discovery.

    Tests are simply named ``test_function_N``. The docstring for the test (hence
    the test description) includes the name and description of each generator.

    .. versionchanged:: 1.5
        Groups of options are now supported

    .. versionchanged:: 2.0
        You can now pass :func:`cocotb.test` decorator arguments when generating tests.

    .. deprecated:: 2.0
        Use :func:`cocotb.parametrize` instead.
    """

    def __init__(
        self,
        test_function: Callable[..., Coroutine[Trigger, None, None]],
        *args: object,
        **kwargs: object,
    ) -> None:
        warnings.warn(
            "TestFactory is deprecated, use `@cocotb.parametrize` instead",
            DeprecationWarning,
            stacklevel=2,
        )
        self.test_function = test_function
        self.args = args
        self.kwargs_constant = kwargs
        self.kwargs: Dict[
            Union[str, Sequence[str]],
            Union[Sequence[object], Sequence[Sequence[object]]],
        ] = {}
        self._log = logging.getLogger(f"TestFactory({self.test_function.__name__})")

    @overload
    def add_option(self, name: str, optionlist: Sequence[object]) -> None: ...

    @overload
    def add_option(
        self, name: Sequence[str], optionlist: Sequence[Sequence[object]]
    ) -> None: ...

    def add_option(
        self,
        name: Union[str, Sequence[str]],
        optionlist: Union[Sequence[object], Sequence[Sequence[object]]],
    ) -> None:
        """Add a named option to the test.

        Args:
            name:
                An option name, or an iterable of several option names. Passed to test as keyword arguments.

            optionlist:
                A list of possible options for this test knob.
                If N names were specified, this must be a list of N-tuples or
                lists, where each element specifies a value for its respective
                option.

        .. versionchanged:: 1.5
            Groups of options are now supported
        """
        if not isinstance(name, str):
            optionlist = cast("Sequence[Sequence[object]]", optionlist)
            for opt in optionlist:
                if len(name) != len(opt):
                    raise ValueError(
                        "Mismatch between number of options and number of option values in group"
                    )
        self.kwargs[name] = optionlist

    def generate_tests(
        self,
        *,
        prefix: Optional[str] = None,
        postfix: Optional[str] = None,
        stacklevel: int = 0,
        name: Optional[str] = None,
        timeout_time: Optional[float] = None,
        timeout_unit: TimeUnit = "step",
        expect_fail: bool = False,
        expect_error: Union[Type[BaseException], Tuple[Type[BaseException], ...]] = (),
        skip: bool = False,
        stage: int = 0,
    ) -> None:
        """
        Generate an exhaustive set of tests using the cartesian product of the
        possible keyword arguments.

        The generated tests are appended to the namespace of the calling
        module.

        Args:
            prefix:
                Text string to append to start of ``test_function`` name when naming generated test cases.
                This allows reuse of a single ``test_function`` with multiple :class:`TestFactories <.TestFactory>` without name clashes.

                .. deprecated:: 2.0
                    Use the more flexible ``name`` field instead.

            postfix:
                Text string to append to end of ``test_function`` name when naming generated test cases.
                This allows reuse of a single ``test_function`` with multiple :class:`TestFactories <.TestFactory>` without name clashes.

                .. deprecated:: 2.0
                    Use the more flexible ``name`` field instead.
            stacklevel:
                Which stack level to add the generated tests to. This can be used to make a custom TestFactory wrapper.

            name:
                Passed as ``name`` argument to :func:`cocotb.test`.

                .. versionadded:: 2.0

            timeout_time:
                Passed as ``timeout_time`` argument to :func:`cocotb.test`.

                .. versionadded:: 2.0

            timeout_unit:
                Passed as ``timeout_unit`` argument to :func:`cocotb.test`.

                .. versionadded:: 2.0

            expect_fail:
                Passed as ``expect_fail`` argument to :func:`cocotb.test`.

                .. versionadded:: 2.0

            expect_error:
                Passed as ``expect_error`` argument to :func:`cocotb.test`.

                .. versionadded:: 2.0

            skip:
                Passed as ``skip`` argument to :func:`cocotb.test`.

                .. versionadded:: 2.0

            stage:
                Passed as ``stage`` argument to :func:`cocotb.test`.

                .. versionadded:: 2.0
        """

        if prefix is not None:
            warnings.warn(
                "``prefix`` argument is deprecated. Use the more flexible ``name`` field instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        else:
            prefix = ""

        if postfix is not None:
            warnings.warn(
                "``postfix`` argument is deprecated. Use the more flexible ``name`` field instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        else:
            postfix = ""

        # trust the user puts a reasonable stacklevel in
        glbs = cast("FrameType", inspect.stack()[stacklevel][0].f_back).f_globals

        test_func_name = self.test_function.__qualname__ if name is None else name

        for index, testoptions in enumerate(
            dict(zip(self.kwargs, v)) for v in product(*self.kwargs.values())
        ):
            name = f"{prefix}{test_func_name}{postfix}_{(index + 1):03d}"
            doc: str = "Automatically generated test\n\n"

            # preprocess testoptions to split tuples
            testoptions_split: Dict[str, Sequence[object]] = {}
            for optname, optvalue in testoptions.items():
                if isinstance(optname, str):
                    optvalue = cast("Sequence[object]", optvalue)
                    testoptions_split[optname] = optvalue
                else:
                    # previously checked in add_option; ensure nothing has changed
                    optvalue = cast("Sequence[Sequence[object]]", optvalue)
                    assert len(optname) == len(optvalue)
                    for n, v in zip(optname, optvalue):
                        testoptions_split[n] = v

            for optname, optvalue in testoptions_split.items():
                if callable(optvalue):
                    optvalue = cast("FunctionType", optvalue)
                    if optvalue.__doc__ is None:
                        desc = "No docstring supplied"
                    else:
                        desc = optvalue.__doc__.split("\n")[0]
                    doc += f"\t{optname}: {optvalue.__qualname__} ({desc})\n"
                else:
                    doc += f"\t{optname}: {optvalue!r}\n"

            kwargs = self.kwargs_constant.copy()
            kwargs.update(testoptions_split)

            @functools.wraps(self.test_function)
            async def _my_test(dut: object, kwargs: Dict[str, object] = kwargs) -> None:
                await self.test_function(dut, *self.args, **kwargs)

            _my_test.__doc__ = doc
            _my_test.__name__ = name
            _my_test.__qualname__ = name

            if name in glbs:
                self._log.error(
                    "Overwriting %s in module %s. "
                    "This causes a previously defined testcase not to be run. "
                    "Consider using the `name`, `prefix`, or `postfix` arguments to augment the name.",
                    name,
                    glbs["__name__"],
                )

            test = Test(
                func=_my_test,
                name=name,
                module=glbs["__name__"],
                timeout_time=timeout_time,
                timeout_unit=timeout_unit,
                expect_fail=expect_fail,
                expect_error=expect_error,
                skip=skip,
                stage=stage,
            )

            glbs[test.name] = test
