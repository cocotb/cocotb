from typing import List

from cocotb.log import _filter_from_c, _log_from_c  # noqa: F401

file = open("results.log", "w")


def entry_func(argv: List[str]) -> None:
    print("got entry", file=file)


def _sim_event(level: int, message: str) -> None:
    print(f"got event level={level} message={message}", file=file)
