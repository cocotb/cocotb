# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import IPython
from IPython.terminal.ipapp import load_default_config
from IPython.terminal.prompts import Prompts, Token

import cocotb


class SimTimePrompt(Prompts):
    """custom prompt that shows the sim time after a trigger fires"""

    _show_time = 1

    def in_prompt_tokens(self, cli=None):
        tokens = super().in_prompt_tokens()
        if self._show_time == self.shell.execution_count:
            tokens = [
                (Token.Comment, f"sim time: {cocotb.utils.get_sim_time()}"),
                (Token.Text, "\n"),
            ] + tokens
        return tokens


def _runner(shell, x):
    """Handler for async functions"""
    ret = cocotb.scheduler._queue_function(x)
    shell.prompts._show_time = shell.execution_count
    return ret


async def embed(user_ns: dict = {}):
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

    Notes:

        If your simulator does not provide an appropriate ``stdin``, you may
        find you cannot type in the resulting shell. Using simulators in batch
        or non-GUI mode may resolve this. This feature is experimental, and
        not all simulators are supported.
    """
    # ensure cocotb is in the namespace, for convenience
    default_ns = dict(cocotb=cocotb)
    default_ns.update(user_ns)

    # build the config to enable `await`
    c = load_default_config()
    c.TerminalInteractiveShell.loop_runner = lambda x: _runner(shell, x)
    c.TerminalInteractiveShell.autoawait = True
    # Python3 checks SQLite DB accesses to ensure process ID matches the one that opened the DB and is not propogated
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
    @cocotb.external
    def run_shell():
        shell()

    await run_shell()


@cocotb.test()
async def run_ipython(dut):
    """A test that launches an interactive Python shell.

    Do not call this directly - use this as ``make MODULE=cocotb.ipython_support``.

    Within the shell, a global ``dut`` variable pointing to the design will be present.
    """
    await embed(user_ns=dict(dut=dut))
