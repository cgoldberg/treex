# Copyright (c) 2026 Corey Goldberg
# SPDX-License-Identifier: MIT


"""Tests for treex."""

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

import treex.treex as treex


def init_git_repo(path):
    subprocess.run(
        ["git", "init"],
        cwd=path,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )


class TestFormatSize:
    def test_bytes(self):
        assert treex._format_size(0) == "0 B"
        assert treex._format_size(512) == "512 B"
        assert treex._format_size(1023) == "1023 B"

    def test_kilobytes(self):
        assert treex._format_size(1024) == "1.0 KB"
        assert treex._format_size(1536) == "1.5 KB"

    def test_megabytes(self):
        assert treex._format_size(1024 * 1024) == "1.0 MB"
        assert treex._format_size(5 * 1024 * 1024) == "5.0 MB"

    def test_gigabytes(self):
        assert treex._format_size(1024**3) == "1.0 GB"

    def test_terabytes(self):
        assert treex._format_size(1024**4) == "1.0 TB"


class TestFormatModified:
    def test_timestamp(self):
        timestamp = datetime(2026, 9, 16, 14, 32).timestamp()
        assert treex._format_modified(timestamp) == "2026-09-16 14:32"


class TestIsBinaryFile:
    def test_empty_file_is_not_binary(self, tmp_path):
        path = tmp_path / "empty"
        path.write_bytes(b"")
        assert treex._is_binary_file(path) is False

    def test_text_file_is_not_binary(self, tmp_path):
        path = tmp_path / "hello.txt"
        path.write_text("Hello, world!\nThis is text.\n", encoding="utf-8")
        assert treex._is_binary_file(path) is False

    def test_utf8_file_is_not_binary(self, tmp_path):
        path = tmp_path / "unicode.txt"
        path.write_text("Hello 🌎\nCafé\n日本語\n", encoding="utf-8")
        assert treex._is_binary_file(path) is False

    def test_null_byte_is_binary(self, tmp_path):
        path = tmp_path / "binary"
        path.write_bytes(b"hello\x00world")
        assert treex._is_binary_file(path) is True

    def test_invalid_utf8_is_binary(self, tmp_path):
        path = tmp_path / "binary"
        path.write_bytes(b"\xff\xfe\xfd")
        assert treex._is_binary_file(path) is True

    def test_missing_file_is_binary(self, tmp_path):
        path = tmp_path / "does-not-exist"
        assert treex._is_binary_file(path) is True


class TestCountLines:
    def test_empty_file(self, tmp_path):
        path = tmp_path / "empty"
        path.write_bytes(b"")
        assert treex._count_lines(path) == 0

    def test_single_line_with_newline(self, tmp_path):
        path = tmp_path / "file.txt"
        path.write_bytes(b"hello\n")
        assert treex._count_lines(path) == 1

    def test_multiple_lines(self, tmp_path):
        path = tmp_path / "file.txt"
        path.write_bytes(b"one\ntwo\nthree\n")
        assert treex._count_lines(path) == 3

    def test_last_line_without_newline(self, tmp_path):
        path = tmp_path / "file.txt"
        path.write_bytes(b"one\ntwo\nthree")
        assert treex._count_lines(path) == 3

    def test_missing_file(self, tmp_path):
        path = tmp_path / "does-not-exist"
        assert treex._count_lines(path) is None


class TestFileMetadata:
    def test_text_file(self, tmp_path):
        path = tmp_path / "file.txt"
        path.write_bytes(b"one\ntwo\nthree\n")
        size, info, raw_size, modified = treex._file_metadata(path)
        assert size == "14 B"
        assert info == "3 lines"
        assert raw_size == 14
        assert modified is not None

    def test_binary_file(self, tmp_path):
        path = tmp_path / "image.bin"
        path.write_bytes(b"\x00\x01\x02\x03")
        size, info, raw_size, modified = treex._file_metadata(path)
        assert size == "4 B"
        assert info == "[binary]"
        assert raw_size == 4
        assert modified is not None

    def test_empty_file(self, tmp_path):
        path = tmp_path / "empty.txt"
        path.write_bytes(b"")
        size, info, raw_size, modified = treex._file_metadata(path)
        assert size == "0 B"
        assert info == "0 lines"
        assert raw_size == 0
        assert modified is not None

    def test_missing_file(self, tmp_path):
        path = tmp_path / "missing.txt"
        size, info, raw_size, modified = treex._file_metadata(path)
        assert size == "?"
        assert info == "[unreadable]"
        assert raw_size == 0
        assert modified is None


class TestGitIgnore:
    @staticmethod
    def has_entry(output, name):
        return any(line.strip().split()[1] == name for line in output.splitlines())

    def test_enabled_hides_git_and_ignored_files(self, tmp_path, capsys):
        init_git_repo(tmp_path)
        (tmp_path / "ignored.txt").write_text("ignored", encoding="utf-8")
        (tmp_path / "README.md").write_text("hello", encoding="utf-8")
        (tmp_path / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
        gitignore = treex.GitIgnore(tmp_path)
        treex.print_tree(tmp_path, gitignore=gitignore)
        output = capsys.readouterr().out
        assert not self.has_entry(output, ".git")
        assert self.has_entry(output, ".gitignore")
        assert not self.has_entry(output, "ignored.txt")
        assert self.has_entry(output, "README.md")

    def test_disabled_shows_everything(self, tmp_path, capsys):
        init_git_repo(tmp_path)
        (tmp_path / "ignored.txt").write_text("ignored", encoding="utf-8")
        (tmp_path / "README.md").write_text("hello", encoding="utf-8")
        (tmp_path / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
        treex.print_tree(tmp_path, gitignore=None)
        output = capsys.readouterr().out
        assert self.has_entry(output, ".git")
        assert self.has_entry(output, ".gitignore")
        assert self.has_entry(output, "ignored.txt")
        assert self.has_entry(output, "README.md")

    def test_disabled_outside_git_repository(self, tmp_path):
        gitignore = treex.GitIgnore(tmp_path)
        assert gitignore.enabled is False
        assert gitignore.ignored(tmp_path / "file.txt") is False

    def test_detects_git_repository(self, tmp_path):
        init_git_repo(tmp_path)
        gitignore = treex.GitIgnore(tmp_path)
        assert gitignore.enabled is True
        assert gitignore.repo_root == tmp_path.resolve()

    def test_does_not_ignore_normal_file(self, tmp_path):
        init_git_repo(tmp_path)
        (tmp_path / ".gitignore").write_text("*.log\n", encoding="utf-8")
        normal_file = tmp_path / "README.md"
        normal_file.write_text("hello", encoding="utf-8")
        gitignore = treex.GitIgnore(tmp_path)
        assert gitignore.ignored(normal_file) is False

    def test_detects_ignored_file(self, tmp_path):
        init_git_repo(tmp_path)
        (tmp_path / ".gitignore").write_text("*.log\n", encoding="utf-8")
        ignored_file = tmp_path / "debug.log"
        ignored_file.write_text("debug output", encoding="utf-8")
        gitignore = treex.GitIgnore(tmp_path)
        assert gitignore.ignored(ignored_file) is True

    def test_detects_ignored_directory(self, tmp_path):
        init_git_repo(tmp_path)
        (tmp_path / ".gitignore").write_text("build/\n", encoding="utf-8")
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        gitignore = treex.GitIgnore(tmp_path)
        assert gitignore.ignored(build_dir) is True

    def test_ignored_many_returns_ignored_paths(self, tmp_path):
        init_git_repo(tmp_path)
        (tmp_path / ".gitignore").write_text("*.log\nbuild/\n", encoding="utf-8")
        ignored_file = tmp_path / "debug.log"
        ignored_file.touch()
        normal_file = tmp_path / "README.md"
        normal_file.touch()
        ignored_dir = tmp_path / "build"
        ignored_dir.mkdir()
        paths = [ignored_file, normal_file, ignored_dir]
        gitignore = treex.GitIgnore(tmp_path)
        assert gitignore.ignored_many(paths) == {"debug.log", "build"}

    def test_ignored_many_uses_single_subprocess(self, tmp_path):
        init_git_repo(tmp_path)
        (tmp_path / ".gitignore").write_text("*.log\n", encoding="utf-8")
        paths = []
        for name in ("one.log", "two.log", "README.md"):
            path = tmp_path / name
            path.touch()
            paths.append(path)
        gitignore = treex.GitIgnore(tmp_path)
        with patch("treex.treex.subprocess.run", wraps=subprocess.run) as mock_run:
            result = gitignore.ignored_many(paths)
        assert result == {"one.log", "two.log"}
        assert mock_run.call_count == 1

    def test_ignored_many_handles_spaces(self, tmp_path):
        init_git_repo(tmp_path)
        (tmp_path / ".gitignore").write_text("*.log\nbuild output/\n", encoding="utf-8")
        ignored_file = tmp_path / "debug output.log"
        ignored_file.touch()
        ignored_dir = tmp_path / "build output"
        ignored_dir.mkdir()
        paths = [ignored_file, ignored_dir]
        gitignore = treex.GitIgnore(tmp_path)
        assert gitignore.ignored_many(paths) == {"debug output.log", "build output"}

    @patch("treex.treex.subprocess.run")
    def test_git_not_installed(self, mock_run, tmp_path):
        mock_run.side_effect = FileNotFoundError
        gitignore = treex.GitIgnore(tmp_path)
        assert gitignore.enabled is False
        assert gitignore.ignored(tmp_path / "file.txt") is False


class TestTreeEntries:
    def test_tree_entries_sorted_with_directories_first(self, tmp_path):
        (tmp_path / "zebra.txt").touch()
        (tmp_path / "Alpha.txt").touch()
        (tmp_path / "src").mkdir()
        (tmp_path / "Docs").mkdir()
        (tmp_path / ".git").mkdir()
        entries = treex._get_tree_entries(tmp_path, gitignore=None)
        assert [entry.name for entry in entries] == [
            ".git",
            "Docs",
            "src",
            "Alpha.txt",
            "zebra.txt",
        ]

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Not always supported on Windows",
    )
    def test_tree_entries_excludes_symlinks(self, tmp_path):
        target = tmp_path / "target.txt"
        target.touch()
        link = tmp_path / "link.txt"
        link.symlink_to(target)
        entries = treex._get_tree_entries(tmp_path, gitignore=None)
        assert [entry.name for entry in entries] == ["target.txt"]


class TestCollectTree:
    def test_collect_tree(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_bytes(b"print('hello')\n")
        (tmp_path / "README.md").write_bytes(b"# README\n")
        stats = {"directories": 0, "files": 0, "total_size": 0}
        rows = []
        treex._collect_tree(tmp_path, "", stats, None, rows, True, False, True)
        assert [row[0] for row in rows] == [
            "├── src",
            "│   └── main.py",
            "└── README.md",
        ]
        assert rows[0][1] == ("15 B", None, None)
        assert rows[1][1][0] == "15 B"
        assert rows[2][1][0] == "9 B"
        assert stats["directories"] == 1
        assert stats["files"] == 2
        assert stats["total_size"] == (len("print('hello')\n") + len("# README\n"))

    def test_collect_tree_without_metadata(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_bytes(b"print('hello')\n")
        (tmp_path / "README.md").write_bytes(b"# README\n")
        stats = {"directories": 0, "files": 0, "total_size": 0}
        rows = []
        treex._collect_tree(tmp_path, "", stats, None, rows, False, False, True)
        assert [row[0] for row in rows] == [
            "├── src",
            "│   └── main.py",
            "└── README.md",
        ]
        assert all(row[1] is None for row in rows)
        assert stats["directories"] == 1
        assert stats["files"] == 2
        assert stats["total_size"] is None

    def test_collect_tree_without_files(self, tmp_path):
        src = tmp_path / "src"
        nested = src / "nested"
        nested.mkdir(parents=True)
        (src / "main.py").write_bytes(b"12345")
        (nested / "helper.py").write_bytes(b"1234567890")
        (tmp_path / "README.md").write_bytes(b"# README\n")
        stats = {"directories": 0, "files": 0, "total_size": 0}
        rows = []
        treex._collect_tree(tmp_path, "", stats, None, rows, True, False, False)
        assert [row[0] for row in rows] == [
            "└── src",
            "    └── nested",
        ]
        assert rows[0][1] == ("15 B", None, None)
        assert rows[1][1] == ("10 B", None, None)
        assert stats["directories"] == 2
        assert stats["files"] == 3
        assert stats["total_size"] == 24

    def test_collect_tree_without_files_and_without_metadata(self, tmp_path):
        src = tmp_path / "src"
        nested = src / "nested"
        nested.mkdir(parents=True)
        (src / "main.py").write_bytes(b"12345")
        (nested / "helper.py").write_bytes(b"1234567890")
        stats = {"directories": 0, "files": 0, "total_size": 0}
        rows = []
        treex._collect_tree(tmp_path, "", stats, None, rows, False, False, False)
        assert [row[0] for row in rows] == ["└── src", "    └── nested"]
        assert all(row[1] is None for row in rows)
        assert stats["directories"] == 2
        assert stats["files"] == 2
        assert stats["total_size"] is None

    def test_collect_tree_directory_size_includes_nested_files(self, tmp_path):
        src = tmp_path / "src"
        nested = src / "nested"
        nested.mkdir(parents=True)
        (src / "main.py").write_bytes(b"12345")
        (nested / "helper.py").write_bytes(b"1234567890")
        stats = {"directories": 0, "files": 0, "total_size": 0}
        rows = []
        treex._collect_tree(tmp_path, "", stats, None, rows, True, False, True)
        assert rows[0] == ("└── src", ("15 B", None, None))
        assert rows[1] == ("    ├── nested", ("10 B", None, None))
        assert rows[2][0] == "    │   └── helper.py"
        assert rows[3][0] == "    └── main.py"

    def test_collect_tree_empty_directory_size(self, tmp_path):
        (tmp_path / "empty").mkdir()
        stats = {"directories": 0, "files": 0, "total_size": 0}
        rows = []
        treex._collect_tree(tmp_path, "", stats, None, rows, True, False, True)
        assert rows == [("└── empty", ("0 B", None, None))]
        assert stats["directories"] == 1
        assert stats["files"] == 0
        assert stats["total_size"] == 0

    def test_collect_tree_permission_denied(self, tmp_path):
        rows = []
        stats = {"directories": 0, "files": 0, "total_size": 0}
        with patch.object(Path, "iterdir", side_effect=PermissionError):
            treex._collect_tree(tmp_path, "", stats, None, rows, True, False, True)
        assert rows == [("└── [permission denied]", None)]
        assert stats["directories"] == 0
        assert stats["files"] == 0
        assert stats["total_size"] == 0


class TestScanTree:
    def test_include_matches_relative_path(self, tmp_path):
        src = tmp_path / "src"
        tests = tmp_path / "tests"
        src.mkdir()
        tests.mkdir()
        (src / "app.py").touch()
        (tests / "app.py").touch()
        nodes = treex._scan_tree(
            tmp_path,
            None,
            False,
            False,
            include_pattern="src/*.py",
        )
        assert [node["name"] for node in nodes] == ["src"]
        assert [node["name"] for node in nodes[0]["children"]] == ["app.py"]
        assert nodes[0]["contains_match"] is True

    def test_exclude_matches_relative_path(self, tmp_path):
        (tmp_path / "app.py").touch()
        (tmp_path / "test_app.py").touch()
        nodes = treex._scan_tree(
            tmp_path,
            None,
            False,
            False,
            exclude_pattern="test_*.py",
        )
        assert [node["name"] for node in nodes] == ["app.py"]

    def test_include_matches_nested_relative_paths(self, tmp_path):
        nested = tmp_path / "src" / "nested"
        nested.mkdir(parents=True)
        (tmp_path / "src" / "app.py").touch()
        (nested / "helper.py").touch()
        (tmp_path / "other.py").touch()
        nodes = treex._scan_tree(
            tmp_path,
            None,
            False,
            False,
            include_pattern="src/*.py",
        )
        assert [node["name"] for node in nodes] == ["src"]
        assert [node["name"] for node in nodes[0]["children"]] == ["nested", "app.py"]
        assert [node["name"] for node in nodes[0]["children"][0]["children"]] == [
            "helper.py"
        ]
        assert nodes[0]["children"][1]["contains_match"] is True

    def test_exclude_overrides_include(self, tmp_path):
        (tmp_path / "app.py").touch()
        (tmp_path / "test_app.py").touch()
        nodes = treex._scan_tree(
            tmp_path,
            None,
            False,
            False,
            include_pattern="*.py",
            exclude_pattern="test_*.py",
        )
        assert [node["name"] for node in nodes] == ["app.py"]

    def test_include_hides_directories_without_matches(self, tmp_path):
        matching = tmp_path / "matching"
        matching.mkdir()
        (matching / "app.py").touch()
        nonmatching = tmp_path / "nonmatching"
        nonmatching.mkdir()
        (nonmatching / "notes.txt").touch()
        nodes = treex._scan_tree(
            tmp_path,
            None,
            False,
            False,
            include_pattern="*.py",
        )
        assert [node["name"] for node in nodes] == ["matching"]
        assert nodes[0]["contains_match"] is True

    def test_include_regex_matches_relative_path(self, tmp_path):
        src = tmp_path / "src"
        tests = tmp_path / "tests"
        src.mkdir()
        tests.mkdir()
        (src / "app.py").touch()
        (tests / "app.py").touch()
        nodes = treex._scan_tree(
            tmp_path,
            None,
            False,
            False,
            include_regex=re.compile(r"^src/.*\.py$"),
        )
        assert [node["name"] for node in nodes] == ["src"]
        assert [node["name"] for node in nodes[0]["children"]] == ["app.py"]
        assert nodes[0]["contains_match"] is True

    def test_exclude_regex_matches_relative_path(self, tmp_path):
        nested = tmp_path / "src" / "tests"
        nested.mkdir(parents=True)
        (tmp_path / "app.py").touch()
        (nested / "test_app.py").touch()
        nodes = treex._scan_tree(
            tmp_path,
            None,
            False,
            False,
            exclude_regex=re.compile(r"(^|/)tests/"),
        )
        assert [node["name"] for node in nodes] == ["src", "app.py"]
        assert [node["name"] for node in nodes[0]["children"]] == ["tests"]
        assert nodes[0]["children"][0]["children"] == []

    def test_exclude_regex_overrides_include(self, tmp_path):
        (tmp_path / "app.py").touch()
        (tmp_path / "test_app.py").touch()
        nodes = treex._scan_tree(
            tmp_path,
            None,
            False,
            False,
            include_pattern="*.py",
            exclude_regex=re.compile(r"(^|/)test_"),
        )
        assert [node["name"] for node in nodes] == ["app.py"]

    def test_glob_and_regex_include_filters(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").touch()
        (src / "app.txt").touch()
        (tmp_path / "other.py").touch()
        nodes = treex._scan_tree(
            tmp_path,
            None,
            False,
            False,
            include_pattern="src/*",
            include_regex=re.compile(r"\.py$"),
        )
        assert [node["name"] for node in nodes] == ["src"]
        assert [node["name"] for node in nodes[0]["children"]] == ["app.py"]

    def test_max_depth_limits_recursion(self, tmp_path):
        nested = tmp_path / "one" / "two"
        nested.mkdir(parents=True)
        (nested / "file.py").touch()
        nodes = treex._scan_tree(
            tmp_path,
            None,
            False,
            False,
            max_depth=2,
        )
        assert [node["name"] for node in nodes] == ["one"]
        assert [node["name"] for node in nodes[0]["children"]] == ["two"]
        assert nodes[0]["children"][0]["children"] == []

    def test_max_depth_with_include_filter(self, tmp_path):
        nested = tmp_path / "one" / "two"
        nested.mkdir(parents=True)
        (nested / "file.py").touch()
        nodes = treex._scan_tree(
            tmp_path,
            None,
            False,
            False,
            include_pattern="*.py",
            max_depth=2,
        )
        assert nodes == []


class TestFilteredTreeStatistics:
    def test_summary_counts_only_included_files(self, tmp_path):
        (tmp_path / "one.py").write_bytes(b"123")
        (tmp_path / "two.py").write_bytes(b"12345")
        (tmp_path / "notes.txt").write_bytes(b"1234567")
        stats = treex.print_tree(tmp_path, show_tree=False, include_pattern="*.py")
        assert stats["files"] == 2
        assert stats["total_size"] == 8

    def test_directory_size_reflects_filtered_files(self, tmp_path, capsys):
        directory = tmp_path / "src"
        directory.mkdir()
        (directory / "main.py").write_bytes(b"12345")
        (directory / "notes.txt").write_bytes(b"1234567890")
        stats = treex.print_tree(tmp_path, include_pattern="*.py")
        output = capsys.readouterr().out
        src_line = next(line for line in output.splitlines() if "src" in line)
        assert "5 B" in src_line
        assert stats["files"] == 1
        assert stats["total_size"] == 5

    def test_directory_only_mode_preserves_filtered_statistics(self, tmp_path, capsys):
        directory = tmp_path / "src"
        directory.mkdir()
        (directory / "main.py").write_bytes(b"12345")
        (directory / "notes.txt").write_bytes(b"1234567890")
        stats = treex.print_tree(tmp_path, show_files=False, include_pattern="*.py")
        output = capsys.readouterr().out
        assert "src" in output
        assert "main.py" not in output
        assert "notes.txt" not in output
        assert stats["directories"] == 1
        assert stats["files"] == 1
        assert stats["total_size"] == 5

    def test_quiet_mode_with_filters(self, tmp_path, capsys):
        (tmp_path / "main.py").write_bytes(b"12345")
        (tmp_path / "notes.txt").write_bytes(b"1234567890")
        stats = treex.print_tree(tmp_path, show_metadata=False, include_pattern="*.py")
        output = capsys.readouterr().out
        assert "main.py" in output
        assert "notes.txt" not in output
        assert "5 B" not in output
        assert stats["files"] == 1
        assert stats["total_size"] is None

    def test_summary_only_with_filters(self, tmp_path, capsys):
        (tmp_path / "main.py").write_bytes(b"12345")
        (tmp_path / "notes.txt").write_bytes(b"1234567890")
        stats = treex.print_tree(tmp_path, show_tree=False, include_pattern="*.py")
        output = capsys.readouterr().out
        assert output == ""
        assert stats["files"] == 1
        assert stats["total_size"] == 5


class TestPrintTree:
    def test_includes_files_and_directories(self, tmp_path, capsys):
        (tmp_path / "dir").mkdir()
        (tmp_path / "file.txt").write_bytes(b"hello")
        stats = treex.print_tree(tmp_path)
        output = capsys.readouterr().out
        assert "dir" in output
        assert "file.txt" in output
        assert stats["directories"] == 1
        assert stats["files"] == 1
        assert stats["total_size"] == 5

    def test_suppress_tree(self, tmp_path, capsys):
        (tmp_path / "file.txt").write_bytes(b"hello")
        stats = treex.print_tree(tmp_path, show_tree=False)
        output = capsys.readouterr().out
        assert output == ""
        assert stats["files"] == 1
        assert stats["total_size"] == 5

    def test_suppress_metadata(self, tmp_path, capsys):
        (tmp_path / "file.txt").write_bytes(b"hello")
        stats = treex.print_tree(tmp_path, show_metadata=False)
        output = capsys.readouterr().out
        assert output.strip().endswith("file.txt")
        assert "5 B" not in output
        assert stats["files"] == 1
        assert stats["total_size"] is None

    def test_suppress_files(self, tmp_path, capsys):
        (tmp_path / "dir").mkdir()
        (tmp_path / "file.txt").write_bytes(b"hello")
        stats = treex.print_tree(tmp_path, show_files=False)
        output = capsys.readouterr().out
        assert "└── dir" in output
        assert "file.txt" not in output
        assert "0 B" in output
        assert stats["directories"] == 1
        assert stats["files"] == 1
        assert stats["total_size"] == 5

    def test_suppress_files_nested(self, tmp_path, capsys):
        nested = tmp_path / "one" / "two"
        nested.mkdir(parents=True)
        (nested / "file.txt").write_bytes(b"hello")
        stats = treex.print_tree(tmp_path, show_files=False)
        output = capsys.readouterr().out
        assert "└── one" in output
        assert "    └── two" in output
        assert "file.txt" not in output
        assert "5 B" in output
        assert stats["directories"] == 2
        assert stats["files"] == 1
        assert stats["total_size"] == 5

    def test_suppress_files_without_metadata(self, tmp_path, capsys):
        nested = tmp_path / "one" / "two"
        nested.mkdir(parents=True)
        (nested / "file.txt").write_bytes(b"hello")
        stats = treex.print_tree(tmp_path, show_metadata=False, show_files=False)
        output = capsys.readouterr().out
        assert "└── one" in output
        assert "    └── two" in output
        assert "file.txt" not in output
        assert "5 B" not in output
        assert stats["directories"] == 2
        assert stats["files"] == 1
        assert stats["total_size"] is None

    def test_nested_directories(self, tmp_path, capsys):
        nested = tmp_path / "one" / "two"
        nested.mkdir(parents=True)
        (nested / "file.txt").write_bytes(b"hello")
        stats = treex.print_tree(tmp_path)
        output = capsys.readouterr().out
        assert "one" in output
        assert "two" in output
        assert "file.txt" in output
        assert "5 B" in output
        assert stats["directories"] == 2
        assert stats["files"] == 1

    def test_include_matches_relative_path(self, tmp_path, capsys):
        src = tmp_path / "src"
        tests = tmp_path / "tests"
        src.mkdir()
        tests.mkdir()
        (src / "app.py").write_bytes(b"hello")
        (tests / "app.py").write_bytes(b"world")
        stats = treex.print_tree(tmp_path, include_pattern="src/*.py")
        output = capsys.readouterr().out
        assert "src" in output
        assert "app.py" in output
        assert "tests" not in output
        assert stats["files"] == 1
        assert stats["total_size"] == 5

    def test_exclude_matches_relative_path(self, tmp_path, capsys):
        tests = tmp_path / "tests"
        tests.mkdir()
        (tmp_path / "app.py").write_bytes(b"hello")
        (tests / "test_app.py").write_bytes(b"world")
        stats = treex.print_tree(tmp_path, exclude_pattern="tests/*.py")
        output = capsys.readouterr().out
        assert "app.py" in output
        assert "test_app.py" not in output
        assert stats["files"] == 1
        assert stats["total_size"] == 5

    def test_include_matches_nested_relative_paths(self, tmp_path, capsys):
        nested = tmp_path / "src" / "nested"
        nested.mkdir(parents=True)
        (tmp_path / "src" / "app.py").write_bytes(b"hello")
        (nested / "helper.py").write_bytes(b"world")
        (tmp_path / "other.py").write_bytes(b"!")
        stats = treex.print_tree(tmp_path, include_pattern="src/*.py")
        output = capsys.readouterr().out
        assert "app.py" in output
        assert "helper.py" in output
        assert "other.py" not in output
        assert stats["files"] == 2
        assert stats["total_size"] == 10

    def test_include_matches_files_recursively(self, tmp_path, capsys):
        (tmp_path / "main.py").touch()
        (tmp_path / "README.md").touch()
        nested = tmp_path / "src"
        nested.mkdir()
        (nested / "helper.py").touch()
        (nested / "config.json").touch()
        stats = treex.print_tree(tmp_path, include_pattern="*.py")
        output = capsys.readouterr().out
        assert "main.py" in output
        assert "helper.py" in output
        assert "README.md" not in output
        assert "config.json" not in output
        assert "src" in output
        assert stats["files"] == 2
        assert stats["directories"] == 1

    def test_include_is_case_sensitive(self, tmp_path, capsys):
        (tmp_path / "lower.py").touch()
        (tmp_path / "upper.PY").touch()
        stats = treex.print_tree(tmp_path, include_pattern="*.py")
        output = capsys.readouterr().out
        assert "lower.py" in output
        assert "upper.PY" not in output
        assert stats["files"] == 1

    def test_exclude_is_case_sensitive(self, tmp_path, capsys):
        (tmp_path / "lower.py").touch()
        (tmp_path / "upper.PY").touch()
        stats = treex.print_tree(tmp_path, exclude_pattern="*.py")
        output = capsys.readouterr().out
        assert "lower.py" not in output
        assert "upper.PY" in output
        assert stats["files"] == 1

    def test_exclude_matches_filenames_recursively(self, tmp_path, capsys):
        (tmp_path / "main.pyc").touch()
        (tmp_path / "main.py").touch()
        nested = tmp_path / "src"
        nested.mkdir()
        (nested / "helper.pyc").touch()
        (nested / "helper.py").touch()
        stats = treex.print_tree(tmp_path, exclude_pattern="*.pyc")
        output = capsys.readouterr().out
        assert "main.py" in output
        assert "helper.py" in output
        assert "main.pyc" not in output
        assert "helper.pyc" not in output
        assert stats["files"] == 2

    def test_exclude_overrides_include(self, tmp_path, capsys):
        (tmp_path / "app.py").write_bytes(b"hello")
        (tmp_path / "test_app.py").write_bytes(b"world")
        stats = treex.print_tree(
            tmp_path,
            include_pattern="*.py",
            exclude_pattern="test_*.py",
        )
        output = capsys.readouterr().out
        assert "app.py" in output
        assert "test_app.py" not in output
        assert stats["files"] == 1
        assert stats["total_size"] == 5

    def test_include_hides_directories_without_matching_files(self, tmp_path, capsys):
        matching = tmp_path / "matching"
        matching.mkdir()
        (matching / "main.py").touch()
        nonmatching = tmp_path / "nonmatching"
        nonmatching.mkdir()
        (nonmatching / "notes.txt").touch()
        stats = treex.print_tree(tmp_path, include_pattern="*.py")
        output = capsys.readouterr().out
        assert "matching" in output
        assert "main.py" in output
        assert "nonmatching" not in output
        assert "notes.txt" not in output
        assert stats["directories"] == 1
        assert stats["files"] == 1

    def test_include_regex_matches_relative_path(self, tmp_path, capsys):
        src = tmp_path / "src"
        tests = tmp_path / "tests"
        src.mkdir()
        tests.mkdir()
        (src / "app.py").write_bytes(b"hello")
        (tests / "app.py").write_bytes(b"world")
        stats = treex.print_tree(tmp_path, include_regex=re.compile(r"^src/.*\.py$"))
        output = capsys.readouterr().out
        assert "src" in output
        assert "app.py" in output
        assert "tests" not in output
        assert stats["files"] == 1
        assert stats["total_size"] == 5

    def test_exclude_regex_matches_relative_path(self, tmp_path, capsys):
        nested = tmp_path / "src" / "tests"
        nested.mkdir(parents=True)
        (tmp_path / "app.py").write_bytes(b"hello")
        (nested / "test_app.py").write_bytes(b"world")
        stats = treex.print_tree(tmp_path, exclude_regex=re.compile(r"(^|/)tests/"))
        output = capsys.readouterr().out
        assert "app.py" in output
        assert "test_app.py" not in output
        assert stats["files"] == 1
        assert stats["total_size"] == 5

    def test_include_regex_is_case_sensitive(self, tmp_path, capsys):
        (tmp_path / "app.py").write_bytes(b"hello")
        stats = treex.print_tree(tmp_path, include_regex=re.compile(r"\.PY$"))
        output = capsys.readouterr().out
        assert "app.py" not in output
        assert stats["files"] == 0
        assert stats["total_size"] == 0

    def test_exclude_regex_is_case_sensitive(self, tmp_path, capsys):
        (tmp_path / "lower.py").write_bytes(b"hello")
        (tmp_path / "upper.PY").write_bytes(b"world")
        stats = treex.print_tree(tmp_path, exclude_regex=re.compile(r"\.py$"))
        output = capsys.readouterr().out
        assert "lower.py" not in output
        assert "upper.PY" in output
        assert stats["files"] == 1

    def test_exclude_regex_overrides_include_glob(self, tmp_path, capsys):
        (tmp_path / "app.py").write_bytes(b"hello")
        (tmp_path / "test_app.py").write_bytes(b"world")
        stats = treex.print_tree(
            tmp_path,
            include_pattern="*.py",
            exclude_regex=re.compile(r"(^|/)test_"),
        )
        output = capsys.readouterr().out
        assert "app.py" in output
        assert "test_app.py" not in output
        assert stats["files"] == 1
        assert stats["total_size"] == 5

    def test_exclude_glob_overrides_include_regex(self, tmp_path, capsys):
        (tmp_path / "app.py").write_bytes(b"hello")
        (tmp_path / "test_app.py").write_bytes(b"world")
        stats = treex.print_tree(
            tmp_path,
            include_regex=re.compile(r"\.py$"),
            exclude_pattern="test_*.py",
        )
        output = capsys.readouterr().out
        assert "app.py" in output
        assert "test_app.py" not in output
        assert stats["files"] == 1
        assert stats["total_size"] == 5

    def test_glob_and_regex_include_filters(self, tmp_path, capsys):
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_bytes(b"hello")
        (src / "app.txt").write_bytes(b"world")
        (tmp_path / "other.py").write_bytes(b"!")
        stats = treex.print_tree(
            tmp_path,
            include_pattern="src/*",
            include_regex=re.compile(r"\.py$"),
        )
        output = capsys.readouterr().out
        assert "app.py" in output
        assert "app.txt" not in output
        assert "other.py" not in output
        assert stats["files"] == 1
        assert stats["total_size"] == 5

    def test_include_and_exclude_can_be_combined_with_depth(self, tmp_path, capsys):
        (tmp_path / "main.py").write_bytes(b"123")
        (tmp_path / "test_main.py").write_bytes(b"12345")
        nested = tmp_path / "src"
        nested.mkdir()
        (nested / "helper.py").write_bytes(b"1234567")
        deeper = nested / "deeper"
        deeper.mkdir()
        (deeper / "deep.py").write_bytes(b"123456789")
        stats = treex.print_tree(
            tmp_path,
            include_pattern="*.py",
            exclude_pattern="test_*.py",
            max_depth=2,
        )
        output = capsys.readouterr().out
        assert "main.py" in output
        assert "helper.py" in output
        assert "test_main.py" not in output
        assert "deeper" not in output
        assert "deep.py" not in output
        assert stats["files"] == 2
        assert stats["total_size"] == 10

    def test_directory_size_is_recursive(self, tmp_path, capsys):
        directory = tmp_path / "dir"
        nested = directory / "nested"
        nested.mkdir(parents=True)
        (directory / "one.txt").write_bytes(b"12345")
        (nested / "two.txt").write_bytes(b"1234567890")
        treex.print_tree(tmp_path)
        output = capsys.readouterr().out
        directory_line = next(line for line in output.splitlines() if "dir" in line)
        nested_line = next(line for line in output.splitlines() if "nested" in line)
        assert "15 B" in directory_line
        assert "10 B" in nested_line

    def test_directory_size_with_files_suppressed(self, tmp_path, capsys):
        directory = tmp_path / "dir"
        nested = directory / "nested"
        nested.mkdir(parents=True)
        (directory / "one.txt").write_bytes(b"12345")
        (nested / "two.txt").write_bytes(b"1234567890")
        stats = treex.print_tree(tmp_path, show_files=False)
        output = capsys.readouterr().out
        directory_line = next(line for line in output.splitlines() if "dir" in line)
        nested_line = next(line for line in output.splitlines() if "nested" in line)
        assert "one.txt" not in output
        assert "two.txt" not in output
        assert "15 B" in directory_line
        assert "10 B" in nested_line
        assert stats["files"] == 2
        assert stats["total_size"] == 15

    def test_empty_directory_has_zero_size(self, tmp_path, capsys):
        (tmp_path / "empty").mkdir()
        treex.print_tree(tmp_path)
        output = capsys.readouterr().out
        empty_line = next(line for line in output.splitlines() if "empty" in line)
        assert "0 B" in empty_line

    def test_directory_size_respects_gitignore(self, tmp_path, capsys):
        init_git_repo(tmp_path)
        directory = tmp_path / "data"
        directory.mkdir()
        (directory / "included.txt").write_bytes(b"12345")
        (directory / "ignored.txt").write_bytes(b"1234567890")
        (tmp_path / ".gitignore").write_text("data/ignored.txt\n", encoding="utf-8")
        gitignore = treex.GitIgnore(tmp_path)
        treex.print_tree(tmp_path, gitignore=gitignore)
        output = capsys.readouterr().out
        data_line = next(line for line in output.splitlines() if "data" in line)
        assert "5 B" in data_line
        assert "15 B" not in data_line
        assert "ignored.txt" not in output

    def test_permission_denied(self, tmp_path, capsys):
        directory = tmp_path / "restricted"
        directory.mkdir()
        with patch.object(Path, "iterdir", side_effect=PermissionError):
            stats = treex.print_tree(directory)
        output = capsys.readouterr().out
        assert "[permission denied]" in output
        assert stats["directories"] == 0
        assert stats["files"] == 0

    def test_tree_name_width_aligns_file_metadata(self, tmp_path, capsys):
        (tmp_path / "a.txt").write_bytes(b"hello")
        (tmp_path / "long_filename.txt").write_bytes(b"hello")
        treex.print_tree(tmp_path)
        lines = capsys.readouterr().out.splitlines()
        size_positions = [line.index("5 B") for line in lines if ".txt" in line]
        assert len(size_positions) == 2
        assert size_positions[0] == size_positions[1]

    def test_tree_name_width_aligns_directory_and_file_metadata(self, tmp_path, capsys):
        directory = tmp_path / "dir"
        directory.mkdir()
        (directory / "file.txt").write_bytes(b"hello")
        (tmp_path / "long_filename.txt").write_bytes(b"hello")
        treex.print_tree(tmp_path)
        lines = capsys.readouterr().out.splitlines()
        size_positions = [
            line.index("5 B") for line in lines if "dir" in line or ".txt" in line
        ]
        assert len(size_positions) == 3
        assert len(set(size_positions)) == 1


class TestPrintSummary:
    def test_print_summary(self, capsys):
        stats = {
            "directories": 1234,
            "files": 5678,
            "total_size": 1234567,
        }
        treex.print_summary(stats)
        output = capsys.readouterr().out
        assert output == "1,234 directories • 5,678 files • 1.2 MB\n"

    def test_print_summary_small_values(self, capsys):
        stats = {
            "directories": 2,
            "files": 15,
            "total_size": 500,
        }
        treex.print_summary(stats)
        output = capsys.readouterr().out
        assert output == "2 directories • 15 files • 500 B\n"

    def test_print_summary_singular(self, capsys):
        stats = {
            "directories": 1,
            "files": 1,
            "total_size": 5,
        }
        treex.print_summary(stats)
        output = capsys.readouterr().out
        assert output == "1 directory • 1 file • 5 B\n"

    def test_print_summary_with_metadata_suppressed(self, capsys):
        stats = {
            "directories": 1234,
            "files": 5678,
            "total_size": None,
        }
        treex.print_summary(stats)
        output = capsys.readouterr().out
        assert output == "1,234 directories • 5,678 files\n"


class TestPositiveInt:
    def test_valid_positive_integer(self):
        assert treex._positive_int(1) == 1

    @pytest.mark.parametrize("value", ["0", "-1"])
    def test_rejects_zero_and_negative_integers(self, value):
        with pytest.raises(
            treex.argparse.ArgumentTypeError,
            match="must be at least 1",
        ):
            treex._positive_int(value)

    @pytest.mark.parametrize("value", ["abc", "1.5", ""])
    def test_rejects_non_integer_input(self, value):
        with pytest.raises(
            treex.argparse.ArgumentTypeError,
            match="must be a positive integer",
        ):
            treex._positive_int(value)


class TestArgumentParsing:
    def test_defaults(self):
        args = treex.parse_args([])
        assert args.directory == Path()
        assert args.all is False
        assert args.modified is False
        assert args.quiet is False
        assert args.dirs is False
        assert args.summary is False
        assert args.include is None
        assert args.exclude is None
        assert args.include_regex is None
        assert args.exclude_regex is None
        assert args.depth is None

    def test_directory(self):
        args = treex.parse_args(["/tmp/project"])
        assert args.directory == Path("/tmp/project")

    def test_all(self):
        args = treex.parse_args(["--all"])
        assert args.all is True

    def test_modified(self):
        args = treex.parse_args(["--modified"])
        assert args.modified is True

    def test_quiet(self):
        args = treex.parse_args(["--quiet"])
        assert args.quiet is True

    def test_dirs(self):
        args = treex.parse_args(["--dirs"])
        assert args.dirs is True

    def test_summary(self):
        args = treex.parse_args(["--summary"])
        assert args.summary is True

    def test_include(self):
        args = treex.parse_args(["--include", "*.py"])
        assert args.include == "*.py"

    def test_exclude(self):
        args = treex.parse_args(["--exclude", "*.pyc"])
        assert args.exclude == "*.pyc"

    def test_include_regex(self):
        args = treex.parse_args(["--include-regex", r"\.py$"])
        assert args.include_regex == r"\.py$"

    def test_exclude_regex(self):
        args = treex.parse_args(["--exclude-regex", r"test_"])
        assert args.exclude_regex == r"test_"

    def test_depth(self):
        args = treex.parse_args(["--depth", "3"])
        assert args.depth == 3

    @pytest.mark.parametrize("depth", ["0", "-1"])
    def test_depth_must_be_positive(self, depth, capsys):
        with pytest.raises(SystemExit) as exc_info:
            treex.parse_args(["--depth", depth])
        assert exc_info.value.code == 2
        assert "must be at least 1" in capsys.readouterr().err

    def test_depth_must_be_integer(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            treex.parse_args(["--depth", "abc"])
        assert exc_info.value.code == 2
        assert "must be a positive integer" in capsys.readouterr().err

    def test_all_options_combined(self):
        args = treex.parse_args(
            [
                "--all",
                "--modified",
                "--quiet",
                "--dirs",
                "--summary",
                "--include",
                "*.py",
                "--exclude",
                "test_*.py",
                "--include-regex",
                r"^src/",
                "--exclude-regex",
                r"(^|/)generated/",
                "--depth",
                "3",
                "/tmp/project",
            ]
        )
        assert args.directory == Path("/tmp/project")
        assert args.all is True
        assert args.modified is True
        assert args.quiet is True
        assert args.dirs is True
        assert args.summary is True
        assert args.include == "*.py"
        assert args.exclude == "test_*.py"
        assert args.include_regex == r"^src/"
        assert args.exclude_regex == r"(^|/)generated/"
        assert args.depth == 3

    def test_all_short_options_combined(self):
        args = treex.parse_args(
            [
                "-a",
                "-m",
                "-q",
                "-d",
                "-i",
                "*.py",
                "-e",
                "test_*.py",
                "-I",
                r"^src/",
                "-E",
                r"(^|/)generated/",
                "-D",
                "3",
                "-s",
            ]
        )
        assert args.all is True
        assert args.modified is True
        assert args.quiet is True
        assert args.dirs is True
        assert args.include == "*.py"
        assert args.exclude == "test_*.py"
        assert args.include_regex == r"^src/"
        assert args.exclude_regex == r"(^|/)generated/"
        assert args.depth == 3
        assert args.summary is True


class TestMain:
    def test_success(self, tmp_path, capsys):
        (tmp_path / "file.txt").write_text("hello", encoding="utf-8")
        with patch.object(sys, "argv", ["treex", str(tmp_path)]):
            assert treex.main() == 0
        output = capsys.readouterr().out
        assert str(tmp_path) in output
        assert "file.txt" in output
        assert "5 B" in output
        assert "1 file" in output

    def test_dirs(self, tmp_path, capsys):
        directory = tmp_path / "dir"
        directory.mkdir()
        (tmp_path / "file.txt").write_text("hello", encoding="utf-8")
        with patch.object(sys, "argv", ["treex", "--dirs", str(tmp_path)]):
            assert treex.main() == 0
        output = capsys.readouterr().out
        assert str(tmp_path) in output
        assert "dir" in output
        assert "file.txt" not in output
        assert "1 directory" in output
        assert "1 file" in output

    def test_not_a_directory(self, tmp_path, capsys):
        path = tmp_path / "file.txt"
        path.write_text("hello", encoding="utf-8")
        with patch.object(sys, "argv", ["treex", str(path)]):
            assert treex.main() == 1
        assert f"Not a directory: {path}" in capsys.readouterr().err

    def test_keyboard_interrupt(self, tmp_path, capsys):
        with (
            patch.object(sys, "argv", ["treex", str(tmp_path)]),
            patch.object(treex, "print_tree", side_effect=KeyboardInterrupt),
        ):
            assert treex.main() == 130
        assert "Interrupted" in capsys.readouterr().err
