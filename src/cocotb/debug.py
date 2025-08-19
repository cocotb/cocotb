# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os

debug: bool = bool(os.getenv("COCOTB_SCHEDULER_DEBUG"))
"""Global flag to enable additional debugging functionality.

Defaults to ``True`` if the :envvar:`COCOTB_SCHEDULER_DEBUG` environment variable is set,
but can be programmatically set by the user afterwards.

The ``"cocotb"`` logger should have its logging level set to :data:`logging.DEBUG`
to see additional debugging information in the test log.
This can be accomplished by setting the :envvar:`COCOTB_LOG_LEVEL` environment variable
to ``DEBUG``,
or using the following code.

.. code-block:: python

    import logging
    logging.getLogger("cocotb").setLevel(logging.DEBUG)

"""
