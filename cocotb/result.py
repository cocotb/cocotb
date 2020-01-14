# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Potential Ventures Ltd,
#       SolarFlare Communications Inc nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# TODO: Could use cStringIO?
import traceback
import sys
import warnings
from io import StringIO, BytesIO
from cocotb import _py_compat

"""Exceptions and functions for simulation result handling."""

def raise_error(obj, msg):
    """Create a :exc:`TestError` exception and raise it after printing a traceback.

    .. deprecated:: 1.3
        Use ``raise TestError(msg)`` instead of this function. A stacktrace will
        be printed by cocotb automatically if the exception is unhandled.

    Args:
        obj: Object with a log method.
        msg (str): The log message.
    """
    warnings.warn(
        "``raise_error`` is deprecated - use ``raise TestError(msg)`` (or any "
        "other exception type) instead",
        DeprecationWarning, stacklevel=2)
    _raise_error(obj, msg)


def _raise_error(obj, msg):
    exc_info = sys.exc_info()
    # Python 2.6 cannot use named access
    if sys.version_info[0] >= 3:
        buff = StringIO()
        traceback.print_exception(*exc_info, file=buff)
    else:
        buff_bytes = BytesIO()
        traceback.print_exception(*exc_info, file=buff_bytes)
        buff = StringIO(buff_bytes.getvalue().decode("UTF-8"))
    obj.log.error("%s\n%s" % (msg, buff.getvalue()))
    exception = TestError(msg)
    exception.stderr.write(buff.getvalue())
    raise exception


def create_error(obj, msg):
    """Like :func:`raise_error`, but return the exception rather than raise it,
    simply to avoid too many levels of nested `try/except` blocks.

    .. deprecated:: 1.3
        Use ``TestError(msg)`` directly instead of this function.

    Args:
        obj: Object with a log method.
        msg (str): The log message.
    """
    warnings.warn(
        "``create_error`` is deprecated - use ``TestError(msg)`` directly "
        "(or any other exception type) instead",
        DeprecationWarning, stacklevel=2)
    try:
        # use the private version to avoid multiple warnings
        _raise_error(obj, msg)
    except TestError as error:
        return error
    return TestError("Creating error traceback failed")


class ReturnValue(Exception):
    """Helper exception needed for Python versions prior to 3.3."""
    def __init__(self, retval):
        self.retval = retval


class TestComplete(Exception):
    """Exception showing that the test was completed. Sub-exceptions detail the exit status."""
    def __init__(self, *args, **kwargs):
        super(TestComplete, self).__init__(*args, **kwargs)
        self.stdout = StringIO()
        self.stderr = StringIO()


class ExternalException(Exception):
    """Exception thrown by :class:`cocotb.external` functions."""
    def __init__(self, exception):
        self.exception = exception


class TestError(TestComplete):
    """Exception showing that the test was completed with severity Error."""
    pass


class TestFailure(TestComplete, AssertionError):
    """Exception showing that the test was completed with severity Failure."""
    pass


class TestSuccess(TestComplete):
    """Exception showing that the test was completed successfully."""
    pass


class SimFailure(TestComplete):
    """Exception showing that the simulator exited unsuccessfully."""
    pass


class SimTimeoutError(_py_compat.TimeoutError):
    """Exception for when a timeout, in terms of simulation time, occurs."""
    pass
