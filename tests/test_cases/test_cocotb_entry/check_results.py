import re


result = open("results.txt").read()

expected = r"""Ran entry_func: \[.*\]
Ran event_func: 2, Simulator shutdown prematurely
Shutting down
"""

assert re.match(expected, result)
