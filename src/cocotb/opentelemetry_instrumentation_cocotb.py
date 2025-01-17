# PEP 723
# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "opentelemetry-api",
#   "opentelemetry-distro",
#   "opentelemetry-exporter-otlp",
#   "opentelemetry-sdk",
#   "wrapt",
# ]
# ///


"""
Usage
-----

.. code-block:: python

   import os
   import opentelemetry_instrumentation_cocotb
   opentelemetry_instrumentation_cocotb.CocotbInstrumentor().instrument()


Then run with

.. code-block:: console

   opentelemetry-instrument --service_name cocotb --traces_exporter otlp ...

API
---
"""
# pylint: disable=no-value-for-parameter

import inspect
import logging
import os
import typing
from contextlib import suppress

from wrapt import wrap_function_wrapper

from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.instrumentation.utils import unwrap
from opentelemetry.trace import SpanKind, get_tracer

import cocotb
import cocotb_tools


def _with_tracer_wrapper(func):
    """Helper for providing tracer for wrapper functions."""

    def _with_tracer(tracer):
        def wrapper(wrapped, instance, args, kwargs):
            return func(tracer, wrapped, instance, args, kwargs)

        return wrapper

    return _with_tracer


@_with_tracer_wrapper
def _wrap_triggers(tracer, wrapped, instance, args, kwargs):
    """Run tracer."""
    instance_name, func_name = wrapped.__func__.__qualname__.split(".")
    span_name = f"cocotb.triggers.{instance_name}.{func_name}"
    with tracer.start_as_current_span(
        span_name,
        kind=SpanKind.INTERNAL,
    ) as span:
        if span.is_recording():
            qualtype = f"{type(instance).__module__}.{type(instance).__name__}"
            # semantic conventions: https://opentelemetry.io/docs/specs/semconv/general/attributes/#source-code-attributes
            span.set_attribute("code.filepath", inspect.getsourcefile(type(instance)))
            span.set_attribute("code.lineno", inspect.getsourcelines(type(instance))[1])
            span.set_attribute("code.namespace", qualtype)
            span.set_attribute("code.function", func_name)
            if args:
                span.set_attribute("code.function.args", f"{args}")
            if kwargs:
                span.set_attribute("code.function.kwargs", f"{kwargs}")
            # our own attributes (see https://opentelemetry.io/docs/specs/semconv/general/attribute-naming/)
            # 3 span.set_attribute(f"{instance_name}.name", instance.name)
            # loc = f"{inspect.getsourcefile(type(instance))}:{inspect.getsourcelines(type(instance))[1]}"
            # span.set_attribute(f"{instance_name} loc", loc)
            span.set_attribute(f"{instance_name}.type", qualtype)
            span.set_attribute(f"{instance_name}.doc", inspect.getdoc(instance).strip())
            # print("###############", str(wrapped))
            # for attr in dir(wrapped.__func__):
            #     print(attr, getattr(wrapped.__func__, attr))
            # span.set_attribute(f"{instance_name}", str(vars(instance)))
        return wrapped(*args, **kwargs)


class CocotbInstrumentor(BaseInstrumentor):
    """An instrumentor for cocotb.

    See also :class:`BaseInstrumentor`.
    """

    def instrumentation_dependencies(self) -> typing.Collection[str]:
        # return ["cocotb ~= 1.0"]  # instrument cocotb 1.x
        return ""

    def _instrument(self, **kwargs):
        tracer_provider = kwargs.get("tracer_provider")
        tracer = get_tracer(
            __name__,
            "0.0.1",
            tracer_provider,
            schema_url="https://opentelemetry.io/schemas/1.11.0",
        )
        # wrap_function_wrapper(cocotb.triggers.Event, "wait", _wrap_triggers(tracer))
        # wrap_function_wrapper(cocotb.triggers.RisingEdge, "__init__", _wrap_triggers(tracer))
        # wrap_function_wrapper(cocotb.triggers.ReadWrite, "_prime", _wrap_triggers(tracer))
        # wrap_function_wrapper(cocotb.triggers.ReadOnly, "_prime", _wrap_triggers(tracer))
        # wrap_function_wrapper(cocotb.triggers.NextTimeStep, "_prime", _wrap_triggers(tracer))
        # wrap_function_wrapper(cocotb.triggers.Timer, "_prime", _wrap_triggers(tracer))
        # wrap_function_wrapper(cocotb.triggers.Trigger, "_prime", _wrap_triggers(tracer))
        wrap_function_wrapper(cocotb.triggers.Trigger, "_prime", _wrap_triggers(tracer))

    def _uninstrument(self, **kwargs):
        # unwrap(cocotb.triggers.Event, "wait")
        unwrap(cocotb.triggers.Trigger, "_prime")
        # FIXME
