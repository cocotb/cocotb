import pytest


def test_import_bus():
    with pytest.warns(DeprecationWarning):
        import cocotb.bus  # noqa: F401

    with pytest.warns(DeprecationWarning):
        import cocotb.drivers  # noqa: F401

    with pytest.warns(DeprecationWarning):
        import cocotb.monitors  # noqa: F401

    with pytest.warns(DeprecationWarning):
        import cocotb.scoreboard  # noqa: F401
