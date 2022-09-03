from typing import List

from cocotb.log import _filter_from_c, _log_from_c  # noqa: F401


def entry_func(argv: List[str]) -> None:
    with open("results.log", "w") as file:
        print("got entry", file=file)


def _sim_event(message: str) -> None:
    with open("results.log", "a") as file:
        print(f"got event message={message}", file=file)
