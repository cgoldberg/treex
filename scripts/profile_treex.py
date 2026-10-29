#!/usr/bin/env python3
# Copyright (c) 2026 Corey Goldberg
# SPDX-License-Identifier: MIT


"""Profile treex and display the top functions by cumulative runtime.

Usage:
    uv run python scripts/profile_treex.py [--show-output] [treex arguments]

By default, suppresses treex stdout while profiling. Use --show-output
to display the tree as normal.

Adjust TOP_N to control how many functions are displayed.
"""

import cProfile
import os
import pstats
import sys
from contextlib import redirect_stdout
from pathlib import Path

from treex.treex import main

TOP_N = 30


if __name__ == "__main__":
    args = sys.argv[1:]
    show_output = "--show-output" in args
    if show_output:
        args.remove("--show-output")

    sys.argv = ["treex", *args]
    profiler = cProfile.Profile()
    if show_output:
        profiler.runcall(main)
    else:
        with (
            Path(os.devnull).open("w", encoding="utf-8") as sink,
            redirect_stdout(sink),
        ):
            profiler.runcall(main)
    print()
    pstats.Stats(profiler).strip_dirs().sort_stats("cumulative").print_stats(TOP_N)
