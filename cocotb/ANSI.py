''' Copyright (c) 2013 Potential Ventures Ltd
Copyright (c) 2013 SolarFlare Communications Inc
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Potential Ventures Ltd,
      SolarFlare Communications Inc nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. '''

'''
    Some constants for doing ANSI stuff.
'''
# flake8: noqa (skip this file for flake8: pypi.python.org/pypi/flake8)
_ESCAPE = "\033["


BLACK_FG        = _ESCAPE + "30m"
RED_FG          = _ESCAPE + "31m"
GREEN_FG        = _ESCAPE + "32m"
YELLOW_FG       = _ESCAPE + "33m"
BLUE_FG         = _ESCAPE + "34m"
MAGENTA_FG      = _ESCAPE + "35m"
CYAN_FG         = _ESCAPE + "36m"
WHITE_FG        = _ESCAPE + "37m"
DEFAULT_FG      = _ESCAPE + "39m"

BLACK_BG        = _ESCAPE + "40m"
RED_BG          = _ESCAPE + "41m"
GREEN_BG        = _ESCAPE + "42m"
YELLOW_BG       = _ESCAPE + "43m"
BLUE_BG         = _ESCAPE + "44m"
MAGENTA_BG      = _ESCAPE + "45m"
CYAN_BG         = _ESCAPE + "46m"
WHITE_BG        = _ESCAPE + "47m"
DEFAULT_BG      = _ESCAPE + "49m"

DEFAULT         = DEFAULT_BG + DEFAULT_FG
