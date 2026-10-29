# Copyright (c) 2026 Corey Goldberg
# SPDX-License-Identifier: MIT


"""List directory contents as a tree with file and directory metadata.

The directory tree is rendered using Unicode box-drawing characters.

When run inside a Git repository, files and directories ignored by Git
are automatically excluded using applicable `.gitignore` rules. Ignore
matching is handled natively by Gitoxide (`gix`) and does not require
Git to be installed. If the directory is not part of a Git repository,
the filesystem is scanned normally without Git filtering.
"""

import argparse
import fnmatch
import os
import re
import sys
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from ._native import IgnoreMatcher

try:
    __version__ = version("treex-cli")
except PackageNotFoundError:
    __version__ = "unknown"


PROG = "treex"


class GitIgnore:
    """Apply Git ignore rules using Gitoxide when inside a repository."""

    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.enabled = False
        self.repo_root = None
        self.matcher = None
        # Discover the repository and initialize ignore matching
        try:
            self.matcher = IgnoreMatcher(str(self.directory))
        except RuntimeError:
            return
        if self.matcher.repo_root is None:
            self.matcher = None
            return
        # Enable Git support if this is a repository
        self.repo_root = Path(self.matcher.repo_root).resolve()
        self.enabled = True

    def ignored(self, path):
        """Check if Git considers a path ignored."""
        return bool(self.ignored_many([path]))

    def ignored_many(self, paths, directory_flags=None):
        """Return the paths that Git considers ignored."""
        if not self.enabled or self.repo_root is None or self.matcher is None:
            return set()
        candidates = []
        matcher_paths = []
        for path in paths:
            try:
                relative = path.relative_to(self.repo_root)
            except (ValueError, OSError):
                continue
            candidates.append(path)
            is_dir = (
                directory_flags[path]
                if directory_flags is not None and path in directory_flags
                else path.is_dir()
            )
            matcher_paths.append((relative.as_posix(), is_dir))
        if not matcher_paths:
            return set()
        results = self.matcher.ignored_many(matcher_paths)
        return {
            path for path, ignored in zip(candidates, results, strict=True) if ignored
        }


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
        # Check for NUL bytes
        if b"\x00" in chunk:
            return True
        # Treat files that aren't valid UTF-8 as binary
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
    """Collect file metadata, identifying binary files and counting text lines.

    Reads files in chunks to avoid loading large files into memory. Checks
    the initial bytes for NUL characters and invalid UTF-8 to identify binary
    files, and counts lines for text files in a single pass. Empty files are
    handled without opening them. Returns formatted size, line count or file
    status, byte size, and modification time.
    """
    try:
        stat = path.stat()
        size = stat.st_size
        modified = _format_modified(stat.st_mtime)
    except OSError:
        return "?", "[unreadable]", 0, None
    size_text = _format_size(size)
    if size == 0:
        return size_text, "0 lines", size, modified
    try:
        f = path.open("rb")
    except OSError:
        return size_text, "[binary]", size, modified
    with f:
        try:
            chunk = f.read(8192)
        except OSError:
            return size_text, "[binary]", size, modified
        if chunk:
            if b"\x00" in chunk:
                return size_text, "[binary]", size, modified
            try:
                chunk.decode("utf-8")
            except UnicodeDecodeError:
                return size_text, "[binary]", size, modified
        lines = chunk.count(b"\n")
        last_byte = chunk[-1:] if chunk else b""
        has_data = bool(chunk)
        # A short read from a regular file normally means EOF.
        if len(chunk) == 8192:
            try:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    has_data = True
                    lines += chunk.count(b"\n")
                    last_byte = chunk[-1:]
            except OSError:
                return size_text, "[unreadable]", size, modified
    if has_data and last_byte != b"\n":
        lines += 1
    return size_text, f"{lines:,} lines", size, modified


def _get_tree_entries(path, gitignore):
    """Get entries to include in the tree with cached type information."""
    typed_entries = []
    try:
        # Use os.scandir() instead of Path.iterdir(): DirEntry caches
        # filesystem metadata, reducing extra system calls for type checks.
        entries = os.scandir(path)
    except PermissionError:
        return None
    with entries:
        for dir_entry in entries:
            if dir_entry.is_symlink():
                continue
            is_dir = dir_entry.is_dir(follow_symlinks=False)
            is_file = dir_entry.is_file(follow_symlinks=False)
            typed_entries.append((Path(dir_entry.path), is_dir, is_file))
    if gitignore is not None:
        typed_entries = [item for item in typed_entries if item[0].name != ".git"]
        if gitignore.enabled and gitignore.repo_root is not None:
            directory_flags = {entry: is_dir for entry, is_dir, _ in typed_entries}
            ignored = gitignore.ignored_many(
                [entry for entry, _, _ in typed_entries],
                directory_flags,
            )
            typed_entries = [item for item in typed_entries if item[0] not in ignored]
    typed_entries.sort(key=lambda item: (item[2], item[0].name.casefold()))
    return typed_entries


def _matches_pattern(path, pattern):
    """Match a relative path using a case-sensitive glob."""
    return pattern is not None and fnmatch.fnmatchcase(path, pattern)


def _scan_tree(
    path,
    gitignore,
    show_metadata,
    show_modified,
    include_pattern=None,
    exclude_pattern=None,
    include_regex=None,
    exclude_regex=None,
    max_depth=None,
    depth=0,
    root=None,
    relative_prefix="",
):
    """Scan and filter the tree, returning nodes for rendering.

    The starting directory has depth 0. Its immediate entries have
    depth 1. Directories at the depth limit are shown without
    descending into them. Include/exclude patterns and regular
    expressions match paths relative to the starting directory.
    Directories are retained only when they contain matching files.
    Directory sizes include only files within the permitted depth
    that pass the include/exclude filters.
    """
    if root is None:
        path = path.resolve()
        root = path
    if max_depth is not None and depth >= max_depth:
        return []
    entries = _get_tree_entries(path, gitignore)
    if entries is None:
        return [
            {
                "name": "[permission denied]",
                "kind": "error",
                "children": [],
                "size": 0,
                "info": None,
                "modified": None,
                "contains_match": False,
            }
        ]
    nodes = []
    has_include = include_pattern is not None or include_regex is not None
    for entry, is_dir, is_file in entries:
        name = entry.name
        relative_path = f"{relative_prefix}/{name}" if relative_prefix else name
        if _matches_pattern(relative_path, exclude_pattern):
            continue
        if exclude_regex is not None and exclude_regex.search(relative_path):
            continue
        if is_dir:
            entry_depth = depth + 1
            if max_depth is not None and entry_depth >= max_depth:
                children = []
            else:
                children = _scan_tree(
                    entry,
                    gitignore,
                    show_metadata,
                    show_modified,
                    include_pattern,
                    exclude_pattern,
                    include_regex,
                    exclude_regex,
                    max_depth,
                    entry_depth,
                    root,
                    relative_path,
                )
            contains_match = any(child["contains_match"] for child in children)
            if has_include and not contains_match:
                continue
            size = (
                sum(child["size"] or 0 for child in children) if show_metadata else None
            )
            nodes.append(
                {
                    "name": name,
                    "kind": "directory",
                    "children": children,
                    "size": size,
                    "info": None,
                    "modified": None,
                    "contains_match": contains_match,
                }
            )
            continue
        if not is_file:
            continue
        if include_pattern is not None and not _matches_pattern(
            relative_path,
            include_pattern,
        ):
            continue
        if include_regex is not None and not include_regex.search(relative_path):
            continue
        if show_metadata:
            size_text, info, size, modified = _file_metadata(entry)
        else:
            size_text, info, size, modified = None, None, None, None
        nodes.append(
            {
                "name": name,
                "kind": "file",
                "children": [],
                "size": size,
                "size_text": size_text,
                "info": info,
                "modified": modified if show_modified else None,
                "contains_match": True,
            }
        )
    return nodes


def _collect_stats(nodes, stats):
    """Add node counts and sizes to the summary statistics."""
    for node in nodes:
        if node["kind"] == "directory":
            stats["directories"] += 1
            _collect_stats(node["children"], stats)
        elif node["kind"] == "file":
            stats["files"] += 1
            if stats["total_size"] is not None:
                stats["total_size"] += node["size"]


def _render_tree(nodes, prefix, rows, show_metadata, show_files):
    """Render nodes as tree rows."""
    visible = [node for node in nodes if show_files or node["kind"] != "file"]
    for index, node in enumerate(visible):
        is_last = index == len(visible) - 1
        connector = "└── " if is_last else "├── "
        tree_name = prefix + connector + node["name"]
        if node["kind"] == "error":
            rows.append((tree_name, None))
            continue
        if node["kind"] == "directory":
            metadata = (
                (_format_size(node["size"]), None, None) if show_metadata else None
            )
            rows.append((tree_name, metadata))
            extension = "    " if is_last else "│   "
            _render_tree(
                node["children"],
                prefix + extension,
                rows,
                show_metadata,
                show_files,
            )
        elif show_files:
            metadata = None
            if show_metadata:
                metadata = (
                    node["size_text"],
                    node["info"],
                    node["modified"],
                )
            rows.append((tree_name, metadata))


def _collect_tree(
    path,
    prefix,
    stats,
    gitignore,
    rows,
    show_metadata,
    show_modified,
    show_files,
    include_pattern=None,
    exclude_pattern=None,
    include_regex=None,
    exclude_regex=None,
    max_depth=None,
):
    """Collect filtered tree rows and update summary statistics."""
    if not show_metadata:
        stats["total_size"] = None
    nodes = _scan_tree(
        Path(path),
        gitignore,
        show_metadata,
        show_modified,
        include_pattern,
        exclude_pattern,
        include_regex,
        exclude_regex,
        max_depth,
    )
    _collect_stats(nodes, stats)
    _render_tree(nodes, prefix, rows, show_metadata, show_files)
    return sum(node["size"] or 0 for node in nodes)


def print_tree(
    directory,
    prefix="",
    stats=None,
    gitignore=None,
    show_metadata=True,
    show_modified=False,
    show_tree=True,
    show_files=True,
    include_pattern=None,
    exclude_pattern=None,
    include_regex=None,
    exclude_regex=None,
    max_depth=None,
):
    """Print the directory tree with aligned metadata."""
    if stats is None:
        stats = {"directories": 0, "files": 0, "total_size": 0}
    rows = []
    _collect_tree(
        Path(directory),
        prefix,
        stats,
        gitignore,
        rows,
        show_metadata,
        show_modified,
        show_files,
        include_pattern,
        exclude_pattern,
        include_regex,
        exclude_regex,
        max_depth,
    )
    if show_tree:
        # Align metadata with the longest tree/name
        max_width = max((len(tree_name) for tree_name, _ in rows), default=0)
        for tree_name, metadata in rows:
            if metadata is None:
                print(tree_name)
                continue
            size_text, info, modified = metadata
            output = f"{tree_name:<{max_width}}{size_text:>10}"
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


def _positive_int(value):
    """Parse a positive integer."""
    try:
        number = int(value)
    except ValueError:
        msg = "must be a positive integer"
        raise argparse.ArgumentTypeError(msg) from None
    if number < 1:
        msg = "must be at least 1"
        raise argparse.ArgumentTypeError(msg)
    return number


def parse_args(argv=None):
    """Parse command-line arguments."""

    def formatter(prog):
        return argparse.HelpFormatter(
            prog,
            width=80,
            max_help_position=32,
        )

    parser = argparse.ArgumentParser(
        description="List directory contents as a tree "
        "with file and directory metadata.",
        usage=f"{PROG} [OPTIONS] [directory]",
        formatter_class=formatter,
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=Path(),
        type=Path,
        help="directory to scan (default: current directory)",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"{PROG} {__version__}",
        help="show version information and exit",
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
    parser.add_argument(
        "-i",
        "--include",
        metavar="PATTERN",
        help="include paths matching a glob pattern",
    )
    parser.add_argument(
        "-e",
        "--exclude",
        metavar="PATTERN",
        help="exclude paths matching a glob pattern",
    )
    parser.add_argument(
        "-I",
        "--include-regex",
        metavar="PATTERN",
        help="include paths matching a regular expression",
    )
    parser.add_argument(
        "-E",
        "--exclude-regex",
        metavar="PATTERN",
        help="exclude paths matching a regular expression",
    )
    parser.add_argument(
        "-D",
        "--depth",
        type=_positive_int,
        metavar="DEPTH",
        help="limit levels displayed below starting directory",
    )
    return parser.parse_args(argv)


def main():
    try:
        args = parse_args()
        path = args.directory
        if not path.is_dir():
            print(f"Not a directory: {path}", file=sys.stderr)
            return 1
        try:
            include_regex = (
                re.compile(args.include_regex)
                if args.include_regex is not None
                else None
            )
            exclude_regex = (
                re.compile(args.exclude_regex)
                if args.exclude_regex is not None
                else None
            )
        except re.error as exc:
            print(f"Invalid regular expression: {exc}", file=sys.stderr)
            return 2
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
            include_pattern=args.include,
            exclude_pattern=args.exclude,
            include_regex=include_regex,
            exclude_regex=exclude_regex,
            max_depth=args.depth,
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
