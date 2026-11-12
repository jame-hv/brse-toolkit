#!/usr/bin/env python3
"""brse-toolkit entry point: brse.py <command> [args]  (run without arguments to list commands)."""
import sys

sys.dont_write_bytecode = True
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from brse.cli import main

sys.exit(main())
