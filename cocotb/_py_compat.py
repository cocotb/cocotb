# Copyright (c) cocotb contributors
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
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
"""
Backports and compatibility shims for newer python features.

These are for internal use - users should use a third party library like `six`
if they want to use these shims in their own code
"""
import abc
import sys

# This is six.integer_types
if sys.version_info.major >= 3:
    integer_types = (int,)
else:
    integer_types = (int, long)  # noqa


# This is essentially six.exec_
if sys.version_info.major == 3:
    # this has to not be a syntax error in py2
    import builtins
    exec_ = getattr(builtins, 'exec')
else:
    # this has to not be a syntax error in py3
    def exec_(_code_, _globs_=None, _locs_=None):
        """Execute code in a namespace."""
        if _globs_ is None:
            frame = sys._getframe(1)
            _globs_ = frame.f_globals
            if _locs_ is None:
                _locs_ = frame.f_locals
            del frame
        elif _locs_ is None:
            _locs_ = _globs_
        exec("""exec _code_ in _globs_, _locs_""")


# this is six.with_metaclass, with a clearer docstring
def with_metaclass(meta, *bases):
    """This provides:

    .. code-block:: python

        class Foo(with_metaclass(Meta, Base1, Base2)): pass

    which is a unifying syntax for:

    .. code-block:: python

        # Python 3
        class Foo(Base1, Base2, metaclass=Meta): pass

        # Python 2
        class Foo(Base1, Base2):
            __metaclass__ = Meta
    """
    # This requires a bit of explanation: the basic idea is to make a dummy
    # metaclass for one level of class instantiation that replaces itself with
    # the actual metaclass.
    class metaclass(type):

        def __new__(cls, name, this_bases, d):
            return meta(name, bases, d)

        @classmethod
        def __prepare__(cls, name, this_bases):
            return meta.__prepare__(name, bases)
    return type.__new__(metaclass, 'temporary_class', (), {})


# this is six.raise_from
if sys.version_info[:2] == (3, 2):
    exec_("""def raise_from(value, from_value):
    try:
        if from_value is None:
            raise value
        raise value from from_value
    finally:
        value = None
    """)
elif sys.version_info[:2] > (3, 2):
    exec_("""def raise_from(value, from_value):
    try:
        raise value from from_value
    finally:
        value = None
    """)
else:
    def raise_from(value, from_value):
        raise value


# backport of Python 3.7's contextlib.nullcontext
class nullcontext(object):
    """Context manager that does no additional processing.
    Used as a stand-in for a normal context manager, when a particular
    block of code is only sometimes used with a normal context manager:

    cm = optional_cm if condition else nullcontext()
    with cm:
        # Perform operation, using optional_cm if condition is True
    """

    def __init__(self, enter_result=None):
        self.enter_result = enter_result

    def __enter__(self):
        return self.enter_result

    def __exit__(self, *excinfo):
        pass


# https://stackoverflow.com/a/38668373
# Backport of abc.ABC, compatible with Python 2 and 3
abc_ABC = abc.ABCMeta('ABC', (object,), {'__slots__': ()})


# source TimeoutError introduced in Python 3.3 to be used by timeout functions
if sys.version_info < (3, 3):
    class TimeoutError(OSError):
        pass
else:
    TimeoutError = TimeoutError
