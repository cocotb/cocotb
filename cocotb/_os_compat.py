# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
OS-specific hacks
"""
import os
import sys

# This is necessary for Windows, which does not support RPATH, causing it
# to not be able to locate the simulator module, which is imported
# unconditionally.

extra_dll_dir = os.path.join(os.path.dirname(__file__), 'libs')

if sys.platform == 'win32' and os.path.isdir(extra_dll_dir):
    if sys.version_info >= (3, 8):
        os.add_dll_directory(extra_dll_dir)
    else:
        os.environ.setdefault('PATH', '')
        os.environ['PATH'] += os.pathsep + extra_dll_dir
