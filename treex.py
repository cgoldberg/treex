# Copyright (c) 2026 Corey Goldberg
# SPDX-License-Identifier: MIT


"""List directory contents as a tree with file and directory metadata.

The directory tree is rendered using Unicode box-drawing characters.

When run inside a Git repository, files and directories ignored by Git
are automatically excluded using Git's own ignore rules. If Git is not
installed, or the directory is not part of a Git repository, the
filesystem is scanned normally without Git filtering.
"""

import argparse
import subprocess
import sys
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
        """Check if Git considers a path ignored."""
        return bool(self.ignored_many([path]))

    def ignored_many(self, paths):
        """Check which paths Git considers ignored."""
        if not self.enabled or self.repo_root is None:
            return set()
        relative_paths = []
        for path in paths:
            try:
                relative = path.resolve().relative_to(self.repo_root)
            except (ValueError, OSError):
                continue
            relative_paths.append(relative.as_posix())
        if not relative_paths:
            return set()
        try:
            # Check all paths in one Git call.
            # -z uses NUL delimiters to safely handle filenames
            # containing special characters.
            result = subprocess.run(
                ["git", "check-ignore", "--stdin", "-z"],
                cwd=self.repo_root,
                input="\0".join(relative_paths) + "\0",
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                check=False,
            )
        except OSError:
            return set()
        if result.returncode not in (0, 1):
            return set()
        return set(result.stdout.split("\0")) - {""}


def _format_size(size):
    """Format bytes as a human-readable size."""
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if size < 1024:
            if unit == "B":
                return f"{size} B"
            return f"{size:.1f} {unit}"
        size /= 1024
    # Anything above 1 TB is shown in TB
    return f"{size:.1f} TB"


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
    entries = [entry for entry in entries if not entry.is_symlink()]
    if gitignore is not None:
        entries = [entry for entry in entries if entry.name != ".git"]
        if gitignore.enabled and gitignore.repo_root is not None:
            ignored = gitignore.ignored_many(entries)
            filtered_entries = []
            for entry in entries:
                try:
                    relative = entry.resolve().relative_to(gitignore.repo_root)
                except (ValueError, OSError):
                    filtered_entries.append(entry)
                    continue
                if relative.as_posix() not in ignored:
                    filtered_entries.append(entry)
            entries = filtered_entries
    entries.sort(key=lambda p: (p.is_file(), p.name.casefold()))
    return entries


def _collect_tree(
    path,
    prefix,
    stats,
    gitignore,
    rows,
    show_metadata,
    show_modified,
    show_files,
):
    """Walk the tree once and collect the output rows."""
    entries = _get_tree_entries(path, gitignore)
    if entries is None:
        rows.append((prefix + "└── [permission denied]", None))
        return 0
    total_size = 0
    # When files are hidden, only directories determine which visible
    # entry is last. Files are still processed for stats and sizes.
    visible_entries = entries
    if not show_files:
        visible_entries = [entry for entry in entries if entry.is_dir()]
    visible_index = 0
    for entry in entries:
        is_visible = show_files or entry.is_dir()
        if is_visible:
            is_last = visible_index == len(visible_entries) - 1
            visible_index += 1
            connector = "└── " if is_last else "├── "
            tree_name = prefix + connector + entry.name
        else:
            tree_name = None
        if entry.is_dir():
            stats["directories"] += 1
            row_index = len(rows)
            rows.append((tree_name, None))
            # Indent nested entries, preserving the tree's vertical branch.
            extension = "    " if is_last else "│   "
            dir_size = _collect_tree(
                entry,
                prefix + extension,
                stats,
                gitignore,
                rows,
                show_metadata,
                show_modified,
                show_files,
            )
            total_size += dir_size
            if show_metadata:
                rows[row_index] = (tree_name, (_format_size(dir_size), None, None))
        elif entry.is_file():
            if show_metadata:
                size_text, info, size, modified = _file_metadata(entry)
                stats["files"] += 1
                stats["total_size"] += size
                total_size += size
                if show_files:
                    timestamp = modified if show_modified else None
                    rows.append((tree_name, (size_text, info, timestamp)))
            else:
                stats["files"] += 1
                stats["total_size"] = None
                if show_files:
                    rows.append((tree_name, None))
    return total_size


def print_tree(
    directory,
    prefix="",
    stats=None,
    gitignore=None,
    show_metadata=True,
    show_modified=False,
    show_tree=True,
    show_files=True,
):
    """Print the directory tree with aligned metadata."""
    if stats is None:
        stats = {"directories": 0, "files": 0, "total_size": 0}
    rows = []
    # Walk the filesystem once and collect the output
    _collect_tree(
        Path(directory),
        prefix,
        stats,
        gitignore,
        rows,
        show_metadata,
        show_modified,
        show_files,
    )
    if show_tree:
        # Align metadata with the longest tree/name
        max_tree_name_width = max((len(tree_name) for tree_name, _ in rows), default=0)
        for tree_name, metadata in rows:
            if metadata is None:
                print(tree_name)
                continue
            size_text, info, modified = metadata
            output = f"{tree_name:<{max_tree_name_width}}{size_text:>10}"
            if info is not None:
                output += f"    {info:<12}"
            if modified is not None:
                output += f"    {modified}"
            print(output)
    return stats


def print_summary(stats):
    """Print a summary of directory/file counts and total size."""
    directories = stats["directories"]
    files = stats["files"]
    total_size = stats["total_size"]
    directory_label = "directory" if directories == 1 else "directories"
    file_label = "file" if files == 1 else "files"
    summary = f"{directories:,} {directory_label} • {files:,} {file_label}"
    if total_size is not None:
        summary += f" • {_format_size(total_size)}"
    print(summary)


def parse_args(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="List directory contents as a tree "
        "with file and directory metadata.",
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
        help="show all files, including those ignored by Git",
    )
    parser.add_argument(
        "-m",
        "--modified",
        action="store_true",
        help="show file modification times",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="don't show file metadata",
    )
    parser.add_argument(
        "-d",
        "--dirs",
        action="store_true",
        help="show directories only",
    )
    parser.add_argument(
        "-s",
        "--summary",
        action="store_true",
        help="show summary only",
    )
    return parser.parse_args(argv)


def main():
    try:
        args = parse_args()
        path = args.directory
        if not path.is_dir():
            print(f"Not a directory: {path}", file=sys.stderr)
            return 1
        # Only initialize Git support if it will be used
        gitignore = None if args.all else GitIgnore(path)
        show_tree = not args.summary
        show_metadata = not args.quiet
        show_files = not args.dirs
        if show_tree:
            print(path)
        stats = print_tree(
            path,
            gitignore=gitignore,
            show_metadata=show_metadata,
            show_modified=args.modified,
            show_tree=show_tree,
            show_files=show_files,
        )
        if show_tree:
            print()
        print_summary(stats)
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130
    else:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
