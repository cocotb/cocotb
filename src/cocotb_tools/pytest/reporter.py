# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Receiving test reports from cocotb using IPC (Inter-Process Communication)."""

from __future__ import annotations

import os
import sys
import traceback
from collections.abc import Generator
from multiprocessing.connection import Client, Listener
from queue import Empty, SimpleQueue
from threading import Thread
from typing import Any


class Reporter:
    def __init__(self):
        self._reports: SimpleQueue[dict[str, Any]] = SimpleQueue()
        self._listener: Listener = Listener()
        self._thread: Thread = Thread(target=self._run)

    def _run(self) -> None:
        while True:
            try:
                with self._listener.accept() as connection:
                    data: dict[str, Any] | None = connection.recv()

                    if data:
                        self._reports.put(data)
                    elif data is None:
                        return

            except BaseException:
                sys.stderr.write(traceback.format_exc())
                sys.stderr.flush()

    def __iter__(self) -> Generator[dict[str, Any], None, None]:
        while True:
            try:
                yield self._reports.get_nowait()
            except Empty:
                return

    def __enter__(self):
        os.environ["COCOTB_PYTEST_REPORTER_ADDRESS"] = str(self._listener.address)
        self._thread.start()
        return self

    def __exit__(self, *args, **kwargs):
        with Client(address=self._listener.address) as client:
            client.send(None)

        self._thread.join()
        self._listener.close()
        del os.environ["COCOTB_PYTEST_REPORTER_ADDRESS"]
