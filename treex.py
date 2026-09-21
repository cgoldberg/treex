# Copyright (c) 2026 Corey Goldberg
# SPDX-License-Identifier: MIT


"""List directory contents as a tree with file metadata.

The directory tree is rendered using Unicode box-drawing characters.

When run inside a Git repository, files and directories ignored by Git
are automatically excluded using Git's own ignore rules. If Git is not
installed, or the directory is not part of a Git repository, the
filesystem is scanned normally without Git filtering.
"""

import argparse
import subprocess
from contextlib import suppress
from datetime import datetime
from pathlib import Path


class GitIgnore:
    """Use Git's ignore rules when available."""

    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.enabled = False
        self.repo_root = None
        # Check Git availability and find the repository root
        with suppress(OSError):
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=self.directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                check=False,
            )
            # Enable Git support if this is a repository
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


def _format_size(size):  # noqa: RET503
    """Format bytes as a human-readable size."""
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{size} B"
            return f"{size:.1f} {unit}"
        size /= 1024


def _format_modified(timestamp):
    """Format a modification timestamp."""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")


def _is_binary_file(path, chunk_size=8192):
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


def _count_lines(path):
    """Count lines without loading the entire file into memory."""
    try:
        with path.open("rb") as f:
            return sum(1 for _ in f)
    except OSError:
        return None


def _file_metadata(path):
    """Get file metadata."""
    try:
        stat = path.stat()
        size = stat.st_size
        modified = _format_modified(stat.st_mtime)
    except OSError:
        return "?", "[unreadable]", 0, None
    size_text = _format_size(size)
    if _is_binary_file(path):
        return size_text, "[binary]", size, modified
    lines = _count_lines(path)
    if lines is None:
        return size_text, "[unreadable]", size, modified
    return size_text, f"{lines:,} lines", size, modified


def _get_tree_entries(path, gitignore):
    """Get entries to include in the tree."""
    try:
        entries = list(path.iterdir())
    except PermissionError:
        return None
    # Filter ignored entries and Git's internal directory
    entries = [
        entry
        for entry in entries
        if not entry.is_symlink()
        and (not gitignore or (entry.name != ".git" and not gitignore.ignored(entry)))
    ]
    # Group directories first and sort names case-insensitive
    entries.sort(key=lambda p: (p.is_file(), p.name.casefold()))
    return entries


def _collect_tree(
    path,
    prefix,
    stats,
    gitignore,
    rows,
    show_modified,
):
    """Walk the tree once and collect the output rows."""
    entries = _get_tree_entries(path, gitignore)
    if entries is None:
        rows.append((prefix + "└── [permission denied]", None))
        return
    for index, entry in enumerate(entries):
        is_last = index == len(entries) - 1
        connector = "└── " if is_last else "├── "
        tree_name = prefix + connector + entry.name
        if entry.is_dir():
            stats["directories"] += 1
            rows.append((tree_name, None))
            # Indent nested entries, preserving the tree's vertical branch
            extension = "    " if is_last else "│   "
            _collect_tree(
                entry,
                prefix + extension,
                stats,
                gitignore,
                rows,
                show_modified,
            )
        elif entry.is_file():
            stats["files"] += 1
            size_text, info, size, modified = _file_metadata(entry)
            stats["total_size"] += size
            timestamp = modified if show_modified else None
            rows.append((tree_name, (size_text, info, timestamp)))


def print_summary(stats):
    print(
        f"{stats['directories']:,} directories • "
        f"{stats['files']:,} files • "
        f"{_format_size(stats['total_size'])}"
    )


def print_tree(
    directory,
    prefix="",
    stats=None,
    gitignore=None,
    show_modified=False,
    show_tree=True,
):
    """Print the directory tree with aligned file metadata."""
    if stats is None:
        stats = {"directories": 0, "files": 0, "total_size": 0}
    rows = []
    # Walk the filesystem once and collect the output
    _collect_tree(Path(directory), prefix, stats, gitignore, rows, show_modified)
    if show_tree:
        # Align file metadata with the longest tree/name
        max_tree_name_width = max(
            (len(tree_name) for tree_name, _ in rows),
            default=0,
        )
        for tree_name, file_info_data in rows:
            if file_info_data is None:
                print(tree_name)
                continue
            size_text, info, modified = file_info_data
            output = f"{tree_name:<{max_tree_name_width}}{size_text:>10}    {info:<10}"
            if modified is not None:
                output += f"    {modified}"
            print(output)
    return stats


def parse_args(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="List directory contents as a tree with file metadata.",
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
        help="show all files (including those ignored by Git)",
    )
    parser.add_argument(
        "-m",
        "--modified",
        action="store_true",
        help="show file modification times",
    )
    parser.add_argument(
        "-s",
        "--summary",
        action="store_true",
        help="show summary only",
    )
    return parser.parse_args(argv)


def main():
    args = parse_args()
    path = args.directory
    if not path.is_dir():
        print(f"Not a directory: {path}")
        return 1
    # Only initialize Git support if it will be used
    gitignore = None if args.all else GitIgnore(path)
    show_tree = not args.summary
    if show_tree:
        print(path)
    stats = print_tree(
        path,
        gitignore=gitignore,
        show_modified=args.modified,
        show_tree=show_tree,
    )
    if show_tree:
        print()
    print_summary(stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
