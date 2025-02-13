# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import (  # noqa: F401  # These types are used in type strings in this module
        Literal,
        TypeAlias,
    )

TimeUnit: "TypeAlias" = 'Literal["step"] | Literal["fs"] | Literal["ps"] | Literal["ns"] | Literal["us"] | Literal["ms"] | Literal["sec"]'
