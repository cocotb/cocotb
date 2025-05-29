# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from typing import Any, Dict, TypeVar

import IPython
from IPython.terminal.ipapp import load_default_config
from IPython.terminal.prompts import Prompts
from pygments.token import Token

import cocotb
from cocotb.task import bridge
from cocotb.utils import get_sim_time

T = TypeVar("T")


class SimTimePrompt(Prompts):
    """custom prompt that shows the sim time after a trigger fires"""

    _show_time = 1

    def in_prompt_tokens(self):
        tokens = super().in_prompt_tokens()
        if self._show_time == self.shell.execution_count:
            tokens = [
                (Token.Comment, f"sim time: {get_sim_time()}"),
                (Token.Text, "\n"),
                *tokens,
            ]
        return tokens


async def embed(user_ns: Dict[str, Any] = {}) -> None:
    """
    Start an IPython shell in the current coroutine.

    Unlike using :func:`IPython.embed` directly, the :keyword:`await` keyword
    can be used directly from the shell to wait for triggers.
    The :keyword:`yield` keyword from the legacy :ref:`yield-syntax` is not supported.

    This coroutine will complete only when the user exits the interactive session.

    Args:
        user_ns:
            The variables to have made available in the shell.
            Passing ``locals()`` is often a good idea.
            ``cocotb`` will automatically be included.

    .. note::
        If your simulator does not provide an appropriate ``stdin``, you may
        find you cannot type in the resulting shell. Using simulators in batch
        or non-GUI mode may resolve this. This feature is experimental, and
        not all simulators are supported.
    """
    # ensure cocotb is in the namespace, for convenience
    default_ns = {"cocotb": cocotb}
    default_ns.update(user_ns)

    def _runner(x):
        """Handler for async functions"""
        nonlocal shell
        ret = cocotb._scheduler_inst._queue_function(x)
        shell.prompts._show_time = shell.execution_count
        return ret

    # build the config to enable `await`
    c = load_default_config()
    c.TerminalInteractiveShell.loop_runner = _runner
    c.TerminalInteractiveShell.autoawait = True
    # Python3 checks SQLite DB accesses to ensure process ID matches the one that opened the DB and is not propagated
    # because we launch IPython in a different process, this will cause unnecessary warnings, so disable the PID check
    c.HistoryAccessor.connection_options = {"check_same_thread": False}
    # create a shell with access to the dut, and cocotb pre-imported
    shell = IPython.terminal.embed.InteractiveShellEmbed(
        user_ns=default_ns,
        config=c,
    )

    # add our custom prompts
    shell.prompts = SimTimePrompt(shell)

    # start the shell in a background thread
    @bridge
    def run_shell() -> None:
        shell()

    await run_shell()


@cocotb.test()
async def run_ipython(dut: Any) -> None:
    """A test that launches an interactive Python shell.

    Do not call this directly - use this as ``make COCOTB_TEST_MODULES=cocotb.ipython_support``.

    Within the shell, a global ``dut`` variable pointing to the design will be present.
    """
    await embed(user_ns={"dut": dut})
