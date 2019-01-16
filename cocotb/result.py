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
# from StringIO import StringIO
from io import StringIO, BytesIO

"""Exceptions and functions for simulation result handling."""

def raise_error(obj, msg):
    """Creates a :exc:`TestError` exception and raises it after printing a traceback.

    Args:
        obj: Object with a log method.
        msg (str): The log message.
    """
    exc_info = sys.exc_info()
    # 2.6 cannot use named access
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

    Args:
        obj: Object with a log method.
        msg (str): The log message.
    """
    try:
        raise_error(obj, msg)
    except TestError as error:
        return error
    return TestError("Creating error traceback failed")


class ReturnValue(Exception):
    """Helper exception needed for Python versions prior to 3.3."""
    def __init__(self, retval):
        self.retval = retval


class TestComplete(Exception):
    """Exception showing that test was completed. Sub-exceptions detail the exit status."""
    def __init__(self, *args, **kwargs):
        super(TestComplete, self).__init__(*args, **kwargs)
        self.stdout = StringIO()
        self.stderr = StringIO()


class ExternalException(Exception):
    """Exception thrown by external functions."""
    def __init__(self, exception):
        self.exception = exception


class TestError(TestComplete):
    """Exception showing that test was completed with severity Error."""
    pass


class TestFailure(TestComplete):
    """Exception showing that test was completed with severity Failure."""
    pass


class TestSuccess(TestComplete):
    """Exception showing that test was completed successfully."""
    pass


class SimFailure(TestComplete):
    """Exception showing that simulator exited unsuccessfully."""
    pass
