# Copyright (c) 2026 Corey Goldberg
# SPDX-License-Identifier: MIT


"""Print a directory tree with file metadata.

The directory tree is rendered using Unicode box-drawing characters. File names are
displayed with their human-readable size and, optionally, modification time. Text
files also include their line count. Binary and unreadable files are marked with
their type.

When run inside a Git repository, files and directories ignored by Git
are automatically excluded using Git's own ignore rules. If Git is not
installed, or the directory is not part of a Git repository, the
filesystem is scanned normally without Git filtering.

Use --all to disable Git ignore filtering and show all files.
Use --width to control the column at which file metadata starts.
Use --modified to show file modification times.
"""

import argparse
import subprocess
from contextlib import suppress
from datetime import datetime
from pathlib import Path

DEFAULT_METADATA_COLUMN = 50


class GitIgnore:
    """Use Git's own ignore machinery when available."""

    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.enabled = False
        self.repo_root = None
        # Git isn't installed or can't be executed.
        with suppress(OSError):
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=self.directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                self.repo_root = Path(result.stdout.strip()).resolve()
                self.enabled = True

    def ignored(self, path):
        """Check if Git considers the path ignored."""
        if not self.enabled:
            return False
        try:
            relative_path = path.resolve().relative_to(self.repo_root)
            result = subprocess.run(
                ["git", "check-ignore", "--quiet", "--", str(relative_path)],
                cwd=self.repo_root,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except (ValueError, OSError):
            return False
        else:
            return result.returncode == 0


def format_size(size):  # noqa: RET503
    """Format bytes as a human-readable size."""
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{size} B"
            return f"{size:.1f} {unit}"
        size /= 1024


def format_modified(timestamp):
    """Format a modification timestamp for display."""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")


def is_binary_file(path, chunk_size=8192):
    """Check if the file appears to be binary."""
    try:
        with path.open("rb") as f:
            chunk = f.read(chunk_size)
        if not chunk:
            return False
        # Check for NUL bytes.
        if b"\x00" in chunk:
            return True
        # Treat files that aren't valid UTF-8 as binary.
        try:
            chunk.decode("utf-8")
        except UnicodeDecodeError:
            return True
        else:
            return False
    except OSError:
        return True


def count_lines(path):
    """Count lines without loading the entire file into memory."""
    try:
        with path.open("rb") as f:
            return sum(1 for _ in f)
    except OSError:
        return None


def file_info(path):
    """Return size, description, raw size, and modification time."""
    try:
        stat = path.stat()
        size = stat.st_size
        modified = format_modified(stat.st_mtime)
    except OSError:
        return "?", "[unreadable]", 0, None
    size_text = format_size(size)
    if is_binary_file(path):
        return size_text, "[binary]", size, modified
    lines = count_lines(path)
    if lines is None:
        return size_text, "[unreadable]", size, modified
    return size_text, f"{lines:,} lines", size, modified


def print_tree(
    directory,
    prefix="",
    stats=None,
    gitignore=None,
    width=DEFAULT_METADATA_COLUMN,
    show_modified=False,
):
    """Recursively print the directory tree."""
    if stats is None:
        stats = {
            "directories": 0,
            "files": 0,
            "total_size": 0,
        }
    path = Path(directory)
    try:
        entries = list(path.iterdir())
    except PermissionError:
        print(prefix + "└── [permission denied]")
        return stats
    # Filter ignored entries before determining which entry is last.
    # Exclude Git's internal repository data.
    visible_entries = [
        entry
        for entry in entries
        if entry.name != ".git" and not (gitignore and gitignore.ignored(entry))
    ]
    # Sort directories before files, group symlinks
    # by target type, and sort names case-insensitive.
    visible_entries.sort(key=lambda p: (p.is_file(), p.name.casefold()))
    for index, entry in enumerate(visible_entries):
        is_last = index == len(visible_entries) - 1
        connector = "└── " if is_last else "├── "
        if entry.is_dir():
            stats["directories"] += 1
            print(prefix + connector + entry.name)
            extension = "    " if is_last else "│   "
            print_tree(
                entry,
                prefix + extension,
                stats,
                gitignore,
                width,
                show_modified,
            )
        elif entry.is_file():
            stats["files"] += 1
            size, info, raw_size, modified = file_info(entry)
            stats["total_size"] += raw_size
            # The complete tree/name portion is padded to the
            # specified width so metadata lines up vertically.
            tree_name = prefix + connector + entry.name
            output = f"{tree_name:<{width}}{size:>10}    {info}"
            if show_modified and modified is not None:
                output += f"    {modified}"
            print(output)
    return stats


def parse_args(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="print a directory tree with file metadata.",
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=Path(),
        type=Path,
        help="directory to scan (default: current directory)",
    )
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="show all files, including ignored by git",
    )
    parser.add_argument(
        "-w",
        "--width",
        type=int,
        default=DEFAULT_METADATA_COLUMN,
        metavar="N",
        help=f"starting column for file metadata (default: {DEFAULT_METADATA_COLUMN})",
    )
    parser.add_argument(
        "-m",
        "--modified",
        action="store_true",
        help="show file modification times",
    )
    return parser.parse_args(argv)


def main():
    args = parse_args()
    path = args.directory
    if not path.is_dir():
        print(f"Not a directory: {path}")
        return 1
    if args.width < 1:
        print("Width must be greater than zero.")
        return 1
    # Only initialize Git integration when it will actually be used.
    gitignore = None if args.all else GitIgnore(path)
    print(path)
    stats = print_tree(
        path, gitignore=gitignore, width=args.width, show_modified=args.modified
    )
    print(
        f"\n{stats['directories']} directories • "
        f"{stats['files']} files • "
        f"{format_size(stats['total_size'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
