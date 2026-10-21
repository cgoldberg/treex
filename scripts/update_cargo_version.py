#!/usr/bin/env python3
# Copyright (c) 2026 Corey Goldberg
# SPDX-License-Identifier: MIT


"""Sync the Cargo package version with the Python project version.

Finds the repository root by searching upward from the current working
directory, reads the version from pyproject.toml, converts dev versions
to Cargo prerelease format when needed, and updates Cargo.toml.
"""

import re
import tomllib
from pathlib import Path


def find_repo_root() -> Path:
    for directory in (Path.cwd(), *Path.cwd().parents):
        if (directory / ".git").exists():
            return directory
    raise FileNotFoundError("Could not find repository root (.git)")


def main():
    repo_root = find_repo_root()
    pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text())
    version = pyproject["project"]["version"].replace(".dev", "-dev.")
    cargo_path = repo_root / "Cargo.toml"
    cargo_text, replacements = re.subn(
        r'(?ms)(^\[package\].*?^version\s*=\s*)("[^"]*")',
        lambda match: f'{match[1]}"{version}"',
        cargo_path.read_text(),
        count=1,
    )
    if replacements != 1:
        raise ValueError("Could not find [package].version in Cargo.toml")
    cargo_path.write_text(cargo_text)
    print(f"Updated Cargo.toml version to {version}")


if __name__ == "__main__":
    main()
