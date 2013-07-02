''' Copyright (c) 2013 Potential Ventures Ltd
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Potential Ventures Ltd nor the
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

"""
Everything related to logging
"""

import os
import logging

import simulator

import cocotb.ANSI as ANSI

# Column alignment
_LEVEL_CHARS    = len("CRITICAL")
_RECORD_CHARS   = 35
_FILENAME_CHARS = 20
_LINENO_CHARS   = 4
_FUNCNAME_CHARS = 32


class SimLogFormatter(logging.Formatter):

    """Log formatter to provide consistent log message handling.

        TODO:
            - Move somewhere sensible
    """
    loglevel2colour = {
        logging.DEBUG   :       "%s",
        logging.INFO    :       ANSI.BLUE_FG + "%s" + ANSI.DEFAULT_FG,
        logging.WARNING :       ANSI.YELLOW_FG + "%s" + ANSI.DEFAULT_FG,
        logging.ERROR   :       ANSI.RED_FG + "%s" + ANSI.DEFAULT_FG,
        logging.CRITICAL:       ANSI.RED_BG + ANSI.BLACK_FG + "%s" +
                                ANSI.DEFAULT_FG + ANSI.DEFAULT_BG}


    def format(self, record):
        """pretify the log output, annotate with simulation time"""
        if record.args:  msg = record.msg % record.args
        else:            msg = record.msg

        msg = SimLogFormatter.loglevel2colour[record.levelno] % msg
        level = SimLogFormatter.loglevel2colour[record.levelno] % \
                                        record.levelname.ljust(_LEVEL_CHARS)

        timeh, timel = simulator.get_sim_time()
        simtime = "% 6d.%02dns" % ((timel/1000), (timel%1000)/10)

        prefix = simtime + ' ' + level + record.name.ljust(_RECORD_CHARS) + \
                 os.path.split(record.filename)[1].rjust(_FILENAME_CHARS) + \
                 ':' + str(record.lineno).ljust(_LINENO_CHARS) + \
                 ' in ' + str(record.funcName).ljust(_FUNCNAME_CHARS) + ' '

        pad = "\n" + " " * (len(prefix) - 10)
        return prefix + pad.join(msg.split('\n'))
