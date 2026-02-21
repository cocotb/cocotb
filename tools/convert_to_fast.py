# /// script
# requires-python = ">=3.9"
# ///
# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Convert standard cocotb tests to use the ``cocotb.fast`` API.

Analyses ``@cocotb.test()`` async functions, identifies hot loops with
signal reads/writes and trigger awaits, and rewrites them to use
:class:`~cocotb.fast.SignalProxy` and the fast mini-scheduler.

Usage::

    uv run tools/convert_to_fast.py path/to/test_module.py
    uv run tools/convert_to_fast.py path/to/test_module.py -o converted.py
    uv run tools/convert_to_fast.py path/to/test_module.py --diff

The converter handles the common patterns well and clearly warns about
anything it cannot convert automatically.  Always review the output.
"""

from __future__ import annotations

import argparse
import ast
import difflib
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Analysis data structures
# ---------------------------------------------------------------------------


@dataclass
class SignalAccess:
    """A signal accessed via ``dut.path.value``."""

    dotted_path: str  # e.g. "dut.stream_in_data"
    proxy_name: str  # e.g. "_proxy_stream_in_data"
    reads: bool = False
    writes: bool = False


@dataclass
class TriggerUsage:
    """An ``await Trigger(...)`` found in a loop."""

    kind: str  # "RisingEdge", "FallingEdge", "ReadOnly", "ReadWrite"
    arg_source: str | None  # e.g. "dut.clk" for edge triggers, None for phase triggers
    var_name: str = ""  # generated variable name, e.g. "_rising_clk"


@dataclass
class Warning:
    """Something that couldn't be auto-converted."""

    lineno: int
    message: str


@dataclass
class LoopAnalysis:
    """Analysis of a hot loop inside a cocotb test."""

    func_name: str
    loop_node: ast.AST
    signals: dict[str, SignalAccess] = field(default_factory=dict)
    triggers: list[TriggerUsage] = field(default_factory=list)
    warnings: list[Warning] = field(default_factory=list)
    # Line range of the loop in the original source
    loop_start: int = 0
    loop_end: int = 0


# ---------------------------------------------------------------------------
# Supported trigger kinds
# ---------------------------------------------------------------------------

SUPPORTED_TRIGGERS = {"RisingEdge", "FallingEdge", "ReadOnly", "ReadWrite"}
EDGE_TRIGGERS = {"RisingEdge", "FallingEdge"}
PHASE_TRIGGERS = {"ReadOnly", "ReadWrite"}

# Triggers we recognise but cannot convert
UNSUPPORTED_TRIGGERS = {"Timer", "Combine", "First", "Join", "NullTrigger"}


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _unparse(node: ast.AST) -> str:
    """Unparse an AST node to source code."""
    return ast.unparse(node)


def _is_value_attr(node: ast.AST) -> bool:
    """Check if *node* is ``<something>.value``."""
    return isinstance(node, ast.Attribute) and node.attr == "value"


def _dotted_name(node: ast.AST) -> str | None:
    """Extract a dotted name like ``dut.stream_in_data`` from an AST node."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def _make_proxy_name(dotted_path: str) -> str:
    """``dut.stream_in_data`` → ``_proxy_stream_in_data``."""
    # Drop the leading "dut." prefix for brevity
    parts = dotted_path.split(".")
    if parts[0] == "dut" and len(parts) > 1:
        parts = parts[1:]
    return "_proxy_" + "_".join(parts)


def _make_trigger_var(kind: str, arg_source: str | None) -> str:
    """Generate a variable name for a trigger instance."""
    base = kind[0].lower() + kind[1:]  # "RisingEdge" → "risingEdge"
    # Convert to snake_case
    name = ""
    for c in base:
        if c.isupper() and name:
            name += "_"
        name += c.lower()
    if arg_source:
        parts = arg_source.split(".")
        suffix = parts[-1]  # e.g. "clk" from "dut.clk"
        name += "_" + suffix
    return "_" + name


# ---------------------------------------------------------------------------
# Loop finder and analyser
# ---------------------------------------------------------------------------


class _LoopAnalyser(ast.NodeVisitor):
    """Walk a loop body and collect signal accesses and trigger awaits."""

    def __init__(self, analysis: LoopAnalysis) -> None:
        self.a = analysis

    def visit_Assign(self, node: ast.Assign) -> None:
        """Detect ``dut.signal.value = expr``."""
        for target in node.targets:
            if _is_value_attr(target):
                path = _dotted_name(target.value)
                if path:
                    sig = self.a.signals.setdefault(
                        path, SignalAccess(path, _make_proxy_name(path))
                    )
                    sig.writes = True
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Detect ``dut.signal.value`` in read context."""
        if _is_value_attr(node):
            # Check this isn't the target of an assignment (handled above)
            path = _dotted_name(node.value)
            if path:
                sig = self.a.signals.setdefault(
                    path, SignalAccess(path, _make_proxy_name(path))
                )
                sig.reads = True
        self.generic_visit(node)

    def visit_Await(self, node: ast.Await) -> None:
        """Detect ``await RisingEdge(dut.clk)`` etc."""
        inner = node.value

        # await TriggerType(...) — direct call
        if isinstance(inner, ast.Call):
            func = inner.func
            func_name = None
            if isinstance(func, ast.Name):
                func_name = func.id
            elif isinstance(func, ast.Attribute):
                func_name = func.attr

            if func_name in SUPPORTED_TRIGGERS:
                arg_src = None
                if inner.args and func_name in EDGE_TRIGGERS:
                    arg_src = _unparse(inner.args[0])
                trig = TriggerUsage(
                    kind=func_name,
                    arg_source=arg_src,
                    var_name=_make_trigger_var(func_name, arg_src),
                )
                # Avoid duplicates
                if not any(
                    t.kind == trig.kind and t.arg_source == trig.arg_source
                    for t in self.a.triggers
                ):
                    self.a.triggers.append(trig)
            elif func_name in UNSUPPORTED_TRIGGERS:
                self.a.warnings.append(
                    Warning(
                        node.lineno,
                        f"Cannot convert: await {func_name}(...) — "
                        f"not supported by fast scheduler",
                    )
                )
            elif func_name and func_name[0].isupper():
                self.a.warnings.append(
                    Warning(
                        node.lineno,
                        f"Unknown trigger type: {func_name} — review manually",
                    )
                )

        # await some_variable — pre-cached trigger
        elif isinstance(inner, ast.Name):
            # We'll handle this during conversion by checking if the variable
            # was assigned from a known trigger
            pass

        self.generic_visit(node)


def _find_hot_loops(func_node: ast.AsyncFunctionDef) -> list[LoopAnalysis]:
    """Find for/while loops that contain await statements."""
    results: list[LoopAnalysis] = []

    for node in ast.walk(func_node):
        if not isinstance(node, (ast.For, ast.While)):
            continue

        # Check if this loop contains any await
        has_await = any(isinstance(child, ast.Await) for child in ast.walk(node))
        if not has_await:
            continue

        analysis = LoopAnalysis(
            func_name=func_node.name,
            loop_node=node,
            loop_start=node.lineno,
            loop_end=node.end_lineno or node.lineno,
        )

        analyser = _LoopAnalyser(analysis)
        analyser.visit(node)

        results.append(analysis)

    return results


# ---------------------------------------------------------------------------
# Test function finder
# ---------------------------------------------------------------------------


def _is_cocotb_test(node: ast.AST) -> bool:
    """Check if *node* is decorated with ``@cocotb.test()``."""
    if not isinstance(node, ast.AsyncFunctionDef):
        return False
    for dec in node.decorator_list:
        if isinstance(dec, ast.Call):
            func = dec.func
            if isinstance(func, ast.Attribute) and func.attr == "test":
                if isinstance(func.value, ast.Name) and func.value.id == "cocotb":
                    return True
            if isinstance(func, ast.Name) and func.id == "test":
                return True
        elif isinstance(dec, ast.Attribute) and dec.attr == "test":
            if isinstance(dec.value, ast.Name) and dec.value.id == "cocotb":
                return True
    return False


# ---------------------------------------------------------------------------
# Code generator
# ---------------------------------------------------------------------------


def _generate_proxy_declarations(signals: dict[str, SignalAccess], indent: str) -> str:
    """Generate SignalProxy declarations."""
    lines: list[str] = []
    for sig in signals.values():
        lines.append(f"{indent}{sig.proxy_name} = fast.SignalProxy({sig.dotted_path})")
    return "\n".join(lines)


def _generate_trigger_declarations(triggers: list[TriggerUsage], indent: str) -> str:
    """Generate fast trigger declarations."""
    lines: list[str] = []
    for trig in triggers:
        if trig.kind in EDGE_TRIGGERS:
            lines.append(
                f"{indent}{trig.var_name} = fast.{trig.kind}({trig.arg_source})"
            )
        else:
            lines.append(f"{indent}{trig.var_name} = fast.{trig.kind}()")
    return "\n".join(lines)


def _convert_loop_body(
    source_lines: list[str],
    analysis: LoopAnalysis,
    base_indent: str,
) -> str:
    """Convert a loop body by replacing signal accesses and triggers."""
    result_lines: list[str] = []

    for lineno in range(analysis.loop_start - 1, analysis.loop_end):
        line = source_lines[lineno]
        converted = _convert_line(line, analysis)
        result_lines.append(converted)

    return "\n".join(result_lines)


def _convert_line(line: str, analysis: LoopAnalysis) -> str:
    """Convert a single line of source code."""
    stripped = line.lstrip()
    indent = line[: len(line) - len(stripped)]

    # --- Signal writes: dut.signal.value = expr → proxy.set_int(expr) ---
    for sig in analysis.signals.values():
        pattern = f"{sig.dotted_path}.value"
        # Assignment: "dut.x.value = expr"
        assign_pattern = f"{pattern} = "
        if stripped.startswith(assign_pattern.lstrip()):
            # Extract the RHS
            idx = line.index(assign_pattern.split(".", 1)[0])
            after_eq = line[line.index("= ", idx) + 2 :].rstrip()
            return f"{indent}{sig.proxy_name}.set_int({after_eq})"

    # --- Signal reads in assignment: x = dut.signal.value → x = proxy.get_int() ---
    for sig in analysis.signals.values():
        pattern = f"{sig.dotted_path}.value"
        if pattern in stripped and "= " in stripped:
            # Check it's on the RHS of an assignment
            parts = stripped.split("=", 1)
            if len(parts) == 2 and pattern in parts[1]:
                lhs = parts[0].rstrip()
                # Simple case: "x = dut.signal.value" or "_ = dut.signal.value"
                rhs = parts[1].strip()
                if rhs == pattern:
                    return f"{indent}{lhs} = {sig.proxy_name}.get_int()"

    # --- Trigger awaits: await RisingEdge(dut.clk) → await _rising_edge_clk ---
    if stripped.startswith("await "):
        for trig in analysis.triggers:
            if trig.kind in EDGE_TRIGGERS and trig.arg_source:
                old_pattern = f"await {trig.kind}({trig.arg_source})"
                if stripped.startswith(old_pattern):
                    return f"{indent}await {trig.var_name}"
            elif trig.kind in PHASE_TRIGGERS:
                old_pattern = f"await {trig.kind}()"
                if stripped.startswith(old_pattern):
                    return f"{indent}await {trig.var_name}"

        # Handle pre-cached triggers: "await rising" where rising = RisingEdge(dut.clk)
        # These are already in good shape — the user just needs to change the import.
        # Leave as-is for now.

    return line


# ---------------------------------------------------------------------------
# Full file converter
# ---------------------------------------------------------------------------


def convert_file(source: str, filename: str = "<input>") -> tuple[str, list[Warning]]:
    """Convert a cocotb test file to use the fast API.

    Returns:
        Tuple of (converted_source, warnings).
    """
    tree = ast.parse(source, filename)
    source_lines = source.splitlines()
    all_warnings: list[Warning] = []

    # Find all cocotb test functions
    test_funcs: list[ast.AsyncFunctionDef] = [
        node for node in ast.walk(tree) if _is_cocotb_test(node)
    ]

    if not test_funcs:
        all_warnings.append(Warning(0, "No @cocotb.test() functions found"))
        return source, all_warnings

    # Analyse each test function
    conversions: list[tuple[ast.AsyncFunctionDef, LoopAnalysis]] = []
    for func in test_funcs:
        loops = _find_hot_loops(func)
        if not loops:
            all_warnings.append(
                Warning(
                    func.lineno,
                    f"Function '{func.name}': no hot loops with await found — skipping",
                )
            )
            continue

        for loop in loops:
            if loop.warnings:
                all_warnings.extend(loop.warnings)
            if loop.signals or loop.triggers:
                conversions.append((func, loop))
            else:
                all_warnings.append(
                    Warning(
                        loop.loop_start,
                        f"Function '{func.name}': loop has no signal accesses or "
                        f"known triggers — skipping",
                    )
                )

    if not conversions:
        all_warnings.append(Warning(0, "No convertible loops found"))
        return source, all_warnings

    # Build the converted source by replacing loop sections
    # Work backwards to preserve line numbers
    result_lines = list(source_lines)

    # Track if we need the fast import
    needs_fast_import = False

    # Sort conversions by start line, reversed, so we can modify bottom-up
    conversions.sort(key=lambda x: x[1].loop_start, reverse=True)

    for _func, analysis in conversions:
        needs_fast_import = True

        # Determine indentation from the loop's first line
        loop_first_line = source_lines[analysis.loop_start - 1]
        loop_indent = loop_first_line[
            : len(loop_first_line) - len(loop_first_line.lstrip())
        ]

        # Generate proxy + trigger declarations
        proxy_decls = _generate_proxy_declarations(analysis.signals, loop_indent)
        trigger_decls = _generate_trigger_declarations(analysis.triggers, loop_indent)

        # Build the replacement block
        replacement_parts: list[str] = []

        # Comment showing what was converted
        replacement_parts.append(
            f"{loop_indent}# --- Converted to cocotb.fast by convert_to_fast.py ---"
        )

        # Proxy declarations
        if proxy_decls:
            replacement_parts.append(proxy_decls)

        # Trigger declarations
        if trigger_decls:
            replacement_parts.append(trigger_decls)

        replacement_parts.append("")

        # Wrap in async def + fast.run
        replacement_parts.append(f"{loop_indent}async def _fast_inner():")

        # Re-indent the converted loop body under _fast_inner
        for lineno in range(analysis.loop_start - 1, analysis.loop_end):
            original = source_lines[lineno]
            converted = _convert_line(original, analysis)
            # Add one level of indentation
            if converted.strip():
                replacement_parts.append(f"    {converted}")
            else:
                replacement_parts.append("")

        replacement_parts.append("")
        replacement_parts.append(f"{loop_indent}await fast.run(_fast_inner())")
        replacement_parts.append(f"{loop_indent}# --- End fast conversion ---")

        # Replace the original loop lines
        replacement = "\n".join(replacement_parts)
        result_lines[analysis.loop_start - 1 : analysis.loop_end] = (
            replacement.splitlines()
        )

    # Add the fast import if needed
    if needs_fast_import:
        result_lines = _add_fast_import(result_lines)

    return "\n".join(result_lines) + "\n", all_warnings


def _add_fast_import(lines: list[str]) -> list[str]:
    """Add ``from cocotb import fast`` import if not already present."""
    # Check if already imported
    for line in lines:
        if "from cocotb import fast" in line or "import cocotb.fast" in line:
            return lines

    # Find a good place to insert — after the last cocotb import
    insert_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(("from cocotb", "import cocotb")):
            insert_idx = i + 1

    if insert_idx > 0:
        lines.insert(insert_idx, "from cocotb import fast")
    else:
        # No cocotb imports found — add at the top after __future__
        for i, line in enumerate(lines):
            if line.strip() and not line.strip().startswith(
                ("#", "from __future__", '"""', "'''")
            ):
                lines.insert(i, "from cocotb import fast")
                lines.insert(i + 1, "")
                break

    return lines


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert standard cocotb tests to use cocotb.fast API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            examples:
              uv run tools/convert_to_fast.py tests/my_test.py
              uv run tools/convert_to_fast.py tests/my_test.py -o tests/my_test_fast.py
              uv run tools/convert_to_fast.py tests/my_test.py --diff
        """),
    )
    parser.add_argument("input", type=Path, help="Input cocotb test file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output file (default: stdout)",
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Show unified diff instead of full output",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Modify the input file in place",
    )
    args = parser.parse_args()

    source = args.input.read_text()
    converted, warnings = convert_file(source, str(args.input))

    # Print warnings to stderr
    if warnings:
        print(f"--- Warnings ({args.input}) ---", file=sys.stderr)
        for w in warnings:
            prefix = f"  line {w.lineno}: " if w.lineno else "  "
            print(f"{prefix}{w.message}", file=sys.stderr)
        print(file=sys.stderr)

    if args.diff:
        diff = difflib.unified_diff(
            source.splitlines(keepends=True),
            converted.splitlines(keepends=True),
            fromfile=str(args.input),
            tofile=str(args.input) + " (fast)",
        )
        sys.stdout.writelines(diff)
    elif args.in_place:
        args.input.write_text(converted)
        print(f"Converted {args.input} in place", file=sys.stderr)
    elif args.output:
        args.output.write_text(converted)
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(converted)


if __name__ == "__main__":
    main()
