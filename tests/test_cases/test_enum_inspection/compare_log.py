# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Summarize the per-signal categorization from enum_inspection.log.

The inspector emits two kinds of records:

    by-name <signal> vpiType=<X> [typespec=<Y> [...]]    # one per known signal
    iter   <iter-kind> found=[name(vpiType),...] count=N # one per iter kind

We parse those into a table, one row per known signal, columns:

    signal | vpiType | typespec | base | members | iter-kinds-found-in

and print it. Exits 0 unconditionally -- the point of the test is to
collect the data, not to fail CI. CI compares the *table* (committed to
expected_results.log) loosely so we can spot regressions.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Known signals we declared in enums.sv, in declaration order.
KNOWN_SIGNALS = [
    "bvec_enum_signal",
    "lvec_enum_signal",
    "int_enum_signal",
    "byte_enum_signal",
    "default_enum_signal",
    "plain_logic_signal",
]

# by-name <signal> vpiType=<X> [typespec=<Y> typedef=<Z> [base=<B> base_size=<N>] [members=[...] count=N]]
# Tokens are space-separated key=value; values themselves can contain '[]'
# and ',' so we walk left-to-right.
BY_NAME_RE = re.compile(r"^by-name\s+(\S+)\s+(.*)$")
# iter <kind> found=[a(t),b(t),...] count=N    OR    iter <kind> NULL
ITER_RE = re.compile(r"^iter\s+(\S+)\s+(.*)$")


def parse_kv(rest: str) -> dict[str, str]:
    """Parse 'k=v k2=v2 ...' where a v may contain '[...]'.

    Bracketed sections are kept verbatim including the brackets.
    """
    out: dict[str, str] = {}
    i = 0
    while i < len(rest):
        # skip spaces
        while i < len(rest) and rest[i].isspace():
            i += 1
        if i >= len(rest):
            break
        # read key up to '='
        j = i
        while j < len(rest) and rest[j] != "=":
            j += 1
        if j >= len(rest):
            # leftover flag, e.g. "NOT_FOUND"
            out[rest[i:].strip()] = ""
            break
        key = rest[i:j]
        i = j + 1
        # read value: if starts with '[', consume to matching ']'
        if i < len(rest) and rest[i] == "[":
            depth = 0
            start = i
            while i < len(rest):
                if rest[i] == "[":
                    depth += 1
                elif rest[i] == "]":
                    depth -= 1
                    if depth == 0:
                        i += 1
                        break
                i += 1
            out[key] = rest[start:i]
        else:
            # read up to next space
            start = i
            while i < len(rest) and not rest[i].isspace():
                i += 1
            out[key] = rest[start:i]
    return out


def parse_log(path: Path) -> tuple[dict[str, dict[str, str]], dict[str, list[str]]]:
    """Returns (by_name, iter_membership).

    by_name[signal] -> dict of fields from the by-name line
    iter_membership[signal] -> sorted list of iteration-kind names where
        this signal appeared
    """
    by_name: dict[str, dict[str, str]] = {}
    iter_membership: dict[str, set[str]] = {s: set() for s in KNOWN_SIGNALS}

    for l in path.read_text().splitlines():
        line = l.strip()
        if not line:
            continue

        m = BY_NAME_RE.match(line)
        if m:
            sig = m.group(1)
            fields = parse_kv(m.group(2))
            by_name[sig] = fields
            continue

        m = ITER_RE.match(line)
        if m:
            kind = m.group(1)
            rest = m.group(2)
            if rest.strip() == "NULL":
                continue
            fields = parse_kv(rest)
            found = fields.get("found", "")
            # found looks like "[a(t),b(t),...]"
            inner = found.strip("[]")
            if not inner:
                continue
            for entry in inner.split(","):
                # entry: "name(vpiType)"
                name = entry.split("(", 1)[0].strip()
                if name in iter_membership:
                    iter_membership[name].add(kind)
            continue

    return by_name, {k: sorted(v) for k, v in iter_membership.items()}


def categorize(fields: dict[str, str], iter_kinds: list[str]) -> dict[str, str]:
    """Distill the raw fields into the columns we print."""
    if not fields:
        # by-name lookup didn't return anything at all -- the signal record
        # was missing from the log (shouldn't happen) or by-name failed but
        # the record was elided. Differentiated from "NOT_FOUND" below.
        return {
            "vpiType": "no-record",
            "typespec": "-",
            "base": "-",
            "members": "-",
            "iters": ",".join(iter_kinds) if iter_kinds else "-",
        }
    if "NOT_FOUND" in fields:
        return {
            "vpiType": "NOT_FOUND",
            "typespec": "-",
            "base": "-",
            "members": "-",
            "iters": ",".join(iter_kinds) if iter_kinds else "-",
        }
    vpi_type = fields.get("vpiType", "?")
    ts = fields.get("typespec", "NULL")
    if ts == "NULL" or not ts:
        ts_col = "NULL"
    else:
        ts_col = ts
    base = fields.get("base", "-") if ts == "vpiEnumTypespec" else "-"
    base_size = fields.get("base_size", "")
    if base != "-" and base_size:
        base = f"{base}[{base_size}]"
    members = fields.get("members", "")
    if members:
        # strip outer []
        members_col = members.strip("[]")
    else:
        members_col = "-"
    return {
        "vpiType": vpi_type,
        "typespec": ts_col,
        "base": base,
        "members": members_col,
        "iters": ",".join(iter_kinds) if iter_kinds else "-",
    }


def render_table(
    by_name: dict[str, dict[str, str]], iters: dict[str, list[str]]
) -> str:
    rows = []
    for sig in KNOWN_SIGNALS:
        cat = categorize(by_name.get(sig, {}), iters.get(sig, []))
        rows.append((sig, cat))

    # Column widths
    cols = ["signal", "vpiType", "typespec", "base", "members", "iters"]
    width = {c: len(c) for c in cols}
    for sig, cat in rows:
        width["signal"] = max(width["signal"], len(sig))
        for k in cols[1:]:
            width[k] = max(width[k], len(cat[k]))

    def fmt_row(values: list[str]) -> str:
        return "  ".join(v.ljust(width[c]) for v, c in zip(values, cols))

    out = []
    out.append(fmt_row(cols))
    out.append(fmt_row(["-" * width[c] for c in cols]))
    for sig, cat in rows:
        out.append(fmt_row([sig] + [cat[c] for c in cols[1:]]))
    return "\n".join(out)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: compare_log.py <enum_inspection.log>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"FAIL: {path} not produced", file=sys.stderr)
        return 1
    by_name, iters = parse_log(path)
    print(render_table(by_name, iters))
    return 0


if __name__ == "__main__":
    sys.exit(main())
