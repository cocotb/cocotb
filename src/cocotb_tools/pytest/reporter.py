# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Receive cocotb test reports from pytest sub-process (simulator) over
IPC (Inter-Process Communication).
"""

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
    """Collecting received cocotb test reports from pytest sub-process over
    IPC (Inter-Process Communication).

    Received cocotb test reports are stored in thread-safe queue.
    """

    def __init__(self):
        """Create new instance of reporter."""
        self._reports: SimpleQueue[dict[str, Any]] = SimpleQueue()
        self._listener: Listener = Listener()
        self._thread: Thread = Thread(target=self._run)

    def _run(self) -> None:
        """Main thread for receiving cocotb test reports from pytest sub-process (simulator)."""
        while True:
            try:
                with self._listener.accept() as connection:
                    data: dict[str, Any] | None = connection.recv()

                    if data:
                        self._reports.put(data)
                    elif data is None:
                        return  # terminate thread

            except BaseException:
                # It should never happen but just in case,
                # catch an exception, print it and accept new connection
                sys.stderr.write(traceback.format_exc())
                sys.stderr.flush()

    def __iter__(self) -> Generator[dict[str, Any], None, None]:
        """Fetch received cocotb test reports from queue.

        .. code:: python

           with Reporter() as reporter:
               for report in reporter:
                   print(report)

        Yields:
            Received cocotb test report from pytest sub-process (simulator).
        """
        while True:
            try:
                yield self._reports.get_nowait()
            except Empty:
                return

    def __enter__(self):
        """Setup environment for receiving cocotb test reports."""
        os.environ["COCOTB_PYTEST_REPORTER_ADDRESS"] = str(self._listener.address)
        self._thread.start()
        return self

    def __exit__(self, *args, **kwargs):
        """Teardown environment for receiving cocotb test reports."""
        with Client(address=self._listener.address) as client:
            client.send(None)  # notify _run thread to exit

        self._thread.join()
        self._listener.close()
        del os.environ["COCOTB_PYTEST_REPORTER_ADDRESS"]
