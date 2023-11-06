# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""
Classes to compare simulation versions.

These are for cocotb-internal use only.

.. warning::
    These classes silently allow comparing versions of different simulators.
"""

from cocotb._vendor.distutils_version import LooseVersion


class ActivehdlVersion(LooseVersion):
    """Version numbering class for Aldec Active-HDL.

    NOTE: unsupported versions exist, e.g.
    ActivehdlVersion("10.5a.12.6914") > ActivehdlVersion("10.5.216.6767")
    """

    pass


class CvcVersion(LooseVersion):
    """Version numbering class for Tachyon DA CVC.

    Example:
        >>> CvcVersion("OSS_CVC_7.00b-x86_64-rhel6x of 07/07/14 (Linux-elf)") > CvcVersion("OSS_CVC_7.00a-x86_64-rhel6x of 07/07/14 (Linux-elf)")
        True
    """

    pass


class GhdlVersion(LooseVersion):
    """Version numbering class for GHDL."""

    pass


class IcarusVersion(LooseVersion):
    """Version numbering class for Icarus Verilog.

    Example:
        >>> IcarusVersion("11.0 (devel)") > IcarusVersion("10.3 (stable)")
        True
        >>> IcarusVersion("10.3 (stable)") <= IcarusVersion("10.3 (stable)")
        True
    """

    pass


class ModelsimVersion(LooseVersion):
    """Version numbering class for Mentor ModelSim."""

    pass


class QuestaVersion(LooseVersion):
    """Version numbering class for Mentor Questa.

    Example:
        >>> QuestaVersion("10.7c 2018.08") > QuestaVersion("10.7b 2018.06")
        True
        >>> QuestaVersion("2020.1 2020.01") > QuestaVersion("10.7c 2018.08")
        True
        >>> QuestaVersion("2020.1 2020.01") == QuestaVersion("2020.1")
        True
        >>> QuestaVersion("2023.1_2 2023.03") > QuestaVersion("2023.1_1")
        True
    """

    def parse(self, vstring):
        # A Questa version string, as returned by the simulator, consists of two
        # space-separated parts. The first part is the actual version number,
        # the second part seems to be the year and month of the initial release.
        # We only need the first part, which is also used in public
        # communication by Siemens.
        try:
            first_component = vstring.split(" ", 1)[0]
        except IndexError:
            first_component = vstring

        super().parse(first_component)


class RivieraVersion(LooseVersion):
    """Version numbering class for Aldec Riviera-PRO.

    Example:
        >>> RivieraVersion("2019.10.138.7537") == RivieraVersion("2019.10.138.7537")
        True
    """

    pass


class VcsVersion(LooseVersion):
    """Version numbering class for Synopsys VCS.

    Example:
        >>> VcsVersion("Q-2020.03-1_Full64") > VcsVersion("K-2015.09_Full64")
        True
    """

    pass


class VerilatorVersion(LooseVersion):
    """Version numbering class for Verilator.

    Example:
        >>> VerilatorVersion("4.032 2020-04-04") > VerilatorVersion("4.031 devel")
        True
    """

    pass


class XceliumVersion(LooseVersion):
    """Version numbering class for Cadence Xcelium.

    Example:
        >>> XceliumVersion("20.06-g183") > XceliumVersion("20.03-s002")
        True
        >>> XceliumVersion("20.07-e501") > XceliumVersion("20.06-g183")
        True
    """

    pass


class IusVersion(XceliumVersion):  # inherit everything from Xcelium
    """Version numbering class for Cadence IUS.

    Example:
        >>> IusVersion("15.20-s050") > IusVersion("15.20-s049")
        True
    """

    pass
