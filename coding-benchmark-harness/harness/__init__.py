"""Coding benchmark harness: HumanEval+ / MBPP+ / Java 8 suites against local models.

Standard library only. See ../DESIGN.md and ../DESIGN-JAVA.md for the specifications and
../notes.md for the implementation log.
"""

import sys

SCHEMA_VERSION = 1
HARNESS_VERSION = "coding-benchmark-harness-v1"

# Python 3.11+ caps integer<->string conversion at 4300 digits, in *both* directions. The
# sandboxed runner lifts the cap for the code it executes, but the harness process also converts:
# `values.decode` does `int(tagged["v"])` and `values.brief` does `repr(...)`. Without this, any
# task whose expected or actual value is a big integer raised ValueError and killed the whole run
# (found by the first full live run, at HumanEval/83 -- a 9876-digit value). Set here so every
# entry point that imports `harness` gets it: run.py, prepare.py, summarize.py and the tests.
if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)
