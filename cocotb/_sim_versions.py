# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""
Classes to compare simulation versions.

These are for cocotb-internal use only.
"""

from distutils.version import LooseVersion


class _LooseVersionTypeChecked(LooseVersion):
    """Do a strict type check so that versions of different simulators cannot be compared.

    Example:
        >>> IcarusVersion("10.3 (stable)") == VerilatorVersion("10.3 (stable)")
        Traceback (most recent call last):
        ...
        TypeError: Comparison not supported between instances of 'IcarusVersion' and 'VerilatorVersion'
        >>> IcarusVersion("10.3 (stable)") != VerilatorVersion("10.3 (stable)")
        Traceback (most recent call last):
        ...
        TypeError: Comparison not supported between instances of 'IcarusVersion' and 'VerilatorVersion'
        >>> IcarusVersion("10.3 (stable)") > VerilatorVersion("10.3 (stable)")
        Traceback (most recent call last):
        ...
        TypeError: '>' not supported between instances of 'IcarusVersion' and 'VerilatorVersion'
        >>> IcarusVersion("10.3 (stable)") >= VerilatorVersion("10.3 (stable)")
        Traceback (most recent call last):
        ...
        TypeError: '>=' not supported between instances of 'IcarusVersion' and 'VerilatorVersion'
        >>> IcarusVersion("10.3 (stable)") < VerilatorVersion("10.3 (stable)")
        Traceback (most recent call last):
        ...
        TypeError: '<' not supported between instances of 'IcarusVersion' and 'VerilatorVersion'
        >>> IcarusVersion("10.3 (stable)") <= VerilatorVersion("10.3 (stable)")
        Traceback (most recent call last):
        ...
        TypeError: '<=' not supported between instances of 'IcarusVersion' and 'VerilatorVersion'
    """

    def __eq__(self, other):
        if not isinstance(self, type(other)) and not isinstance(other, type(self)):
            raise TypeError(
                "Comparison not supported between instances of '{}' and '{}'".format(
                    type(self).__name__, type(other).__name__
                )
            )
        else:
            return super().__eq__(other)

    def __lt__(self, other):
        if not isinstance(self, type(other)) and not isinstance(other, type(self)):
            return NotImplemented
        else:
            return super().__lt__(other)

    def __gt__(self, other):
        if not isinstance(self, type(other)) and not isinstance(other, type(self)):
            return NotImplemented
        else:
            return super().__gt__(other)

    def __le__(self, other):
        if not isinstance(self, type(other)) and not isinstance(other, type(self)):
            return NotImplemented
        else:
            return super().__le__(other)

    def __ge__(self, other):
        if not isinstance(self, type(other)) and not isinstance(other, type(self)):
            return NotImplemented
        else:
            return super().__ge__(other)


class ActivehdlVersion(_LooseVersionTypeChecked):
    """Version numbering class for Aldec Active-HDL.

    NOTE: unsupported versions exist, e.g.
    ActivehdlVersion("10.5a.12.6914") > ActivehdlVersion("10.5.216.6767")
    """


class CvcVersion(_LooseVersionTypeChecked):
    """Version numbering class for Tachyon DA CVC.

    Example:
        >>> CvcVersion("OSS_CVC_7.00b-x86_64-rhel6x of 07/07/14 (Linux-elf)") > CvcVersion("OSS_CVC_7.00a-x86_64-rhel6x of 07/07/14 (Linux-elf)")
        True
    """

    pass


class GhdlVersion(_LooseVersionTypeChecked):
    """Version numbering class for GHDL."""

    pass


class IcarusVersion(_LooseVersionTypeChecked):
    """Version numbering class for Icarus Verilog.

    Example:
        >>> IcarusVersion("11.0 (devel)") > IcarusVersion("10.3 (stable)")
        True
        >>> IcarusVersion("10.3 (stable)") <= IcarusVersion("10.3 (stable)")
        True
    """

    pass


class ModelsimVersion(_LooseVersionTypeChecked):
    """Version numbering class for Mentor ModelSim."""

    pass


class QuestaVersion(_LooseVersionTypeChecked):
    """Version numbering class for Mentor Questa.

    Example:
        >>> QuestaVersion("10.7c 2018.08") > QuestaVersion("10.7b 2018.06")
        True
        >>> QuestaVersion("10.7c 2018.08") < QuestaVersion("2020.1 2020.01")
        True
    """

    pass


class RivieraVersion(_LooseVersionTypeChecked):
    """Version numbering class for Aldec Riviera-PRO.

    Example:
        >>> RivieraVersion("2019.10.138.7537") == RivieraVersion("2019.10.138.7537")
        True
    """

    pass


class VcsVersion(_LooseVersionTypeChecked):
    """Version numbering class for Synopsys VCS.

    Example:
        >>> VcsVersion("Q-2020.03-1_Full64") > VcsVersion("K-2015.09_Full64")
        True
    """

    pass


class VerilatorVersion(_LooseVersionTypeChecked):
    """Version numbering class for Verilator.

    Example:
        >>> VerilatorVersion("4.032 2020-04-04") > VerilatorVersion("4.031 devel")
        True
        >>> VerilatorVersion("4.032 2020-04-04") >= VerilatorVersion("4.032 2020-04-04")
        True
    """

    pass


class XceliumVersion(_LooseVersionTypeChecked):
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
