from __future__ import annotations

from typing import Any


def entry_func(argv: Any) -> None:
    with open("results.log", "w") as file:
        print("got entry", file=file)
