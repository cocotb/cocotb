# Copyright cocotb contributors
# Copyright (c) 2013, 2018 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

from cocotb._py_compat import StrEnum

_ESCAPE = "\033["


class ANSI(StrEnum):
    """ANSI escape codes for coloring output.

    The color names supported are ``[BRIGHT_]{BLACK|RED|GREEN|YELLOW|BLUE|MAGENTA|CYAN|WHITE}{_FG|_BG}``.

    Variables that end in ``_FG`` will color the character or symbol ("foreground")
    and variables that end in ``_BG`` will color the background.

    Foreground and background colors can be combined together with a ``+``.
    Setting a new foreground color will override the previous foreground, likewise with background colors.

    Use ``DEFAULT_FG`` and ``DEFAULT_BG`` to reset the coloring to the default colors for the foreground and background, respectively.
    Or use ``DEFAULT`` to reset both.
    """

    DEFAULT_FG = _ESCAPE + "39m"
    DEFAULT_BG = _ESCAPE + "49m"
    DEFAULT = DEFAULT_BG + DEFAULT_FG

    BLACK_FG = _ESCAPE + "30m"
    RED_FG = _ESCAPE + "31m"
    GREEN_FG = _ESCAPE + "32m"
    YELLOW_FG = _ESCAPE + "33m"
    BLUE_FG = _ESCAPE + "34m"
    MAGENTA_FG = _ESCAPE + "35m"
    CYAN_FG = _ESCAPE + "36m"
    WHITE_FG = _ESCAPE + "37m"

    BLACK_BG = _ESCAPE + "40m"
    RED_BG = _ESCAPE + "41m"
    GREEN_BG = _ESCAPE + "42m"
    YELLOW_BG = _ESCAPE + "43m"
    BLUE_BG = _ESCAPE + "44m"
    MAGENTA_BG = _ESCAPE + "45m"
    CYAN_BG = _ESCAPE + "46m"
    WHITE_BG = _ESCAPE + "47m"

    BRIGHT_BLACK_FG = _ESCAPE + "90m"
    BRIGHT_RED_FG = _ESCAPE + "91m"
    BRIGHT_GREEN_FG = _ESCAPE + "92m"
    BRIGHT_YELLOW_FG = _ESCAPE + "93m"
    BRIGHT_BLUE_FG = _ESCAPE + "94m"
    BRIGHT_MAGENTA_FG = _ESCAPE + "95m"
    BRIGHT_CYAN_FG = _ESCAPE + "96m"
    BRIGHT_WHITE_FG = _ESCAPE + "97m"

    BRIGHT_BLACK_BG = _ESCAPE + "100m"
    BRIGHT_RED_BG = _ESCAPE + "101m"
    BRIGHT_GREEN_BG = _ESCAPE + "102m"
    BRIGHT_YELLOW_BG = _ESCAPE + "103m"
    BRIGHT_BLUE_BG = _ESCAPE + "104m"
    BRIGHT_MAGENTA_BG = _ESCAPE + "105m"
    BRIGHT_CYAN_BG = _ESCAPE + "106m"
    BRIGHT_WHITE_BG = _ESCAPE + "107m"
