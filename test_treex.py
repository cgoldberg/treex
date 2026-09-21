# Copyright (c) 2026 Corey Goldberg
# SPDX-License-Identifier: MIT


"""Tests for treex."""

import subprocess
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

import treex


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

    def test_large_values(self):
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
        path.write_text("hello\n", encoding="utf-8")
        assert treex._count_lines(path) == 1

    def test_multiple_lines(self, tmp_path):
        path = tmp_path / "file.txt"
        path.write_text("one\ntwo\nthree\n", encoding="utf-8")
        assert treex._count_lines(path) == 3

    def test_last_line_without_newline(self, tmp_path):
        path = tmp_path / "file.txt"
        path.write_text("one\ntwo\nthree", encoding="utf-8")
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
        contents = b"\x00\x01\x02\x03"
        path.write_bytes(contents)
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
    def init_git_repo(path):
        subprocess.run(
            ["git", "init"],
            cwd=path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )

    @staticmethod
    def has_entry(output, name):
        return any(line.strip().split()[1] == name for line in output.splitlines())

    def test_enabled_hides_git_and_ignored_files(self, tmp_path, capsys):
        self.init_git_repo(tmp_path)
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
        self.init_git_repo(tmp_path)
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
        subprocess.run(
            ["git", "init"],
            cwd=tmp_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        gitignore = treex.GitIgnore(tmp_path)
        assert gitignore.enabled is True
        assert gitignore.repo_root == tmp_path.resolve()

    def test_does_not_ignore_normal_file(self, tmp_path):
        subprocess.run(
            ["git", "init"],
            cwd=tmp_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        (tmp_path / ".gitignore").write_text("*.log\n", encoding="utf-8")
        normal_file = tmp_path / "README.md"
        normal_file.write_text("hello", encoding="utf-8")
        gitignore = treex.GitIgnore(tmp_path)
        assert gitignore.ignored(normal_file) is False

    def test_detects_ignored_file(self, tmp_path):
        subprocess.run(
            ["git", "init"],
            cwd=tmp_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        (tmp_path / ".gitignore").write_text("*.log\n", encoding="utf-8")
        ignored_file = tmp_path / "debug.log"
        ignored_file.write_text("debug output", encoding="utf-8")
        gitignore = treex.GitIgnore(tmp_path)
        assert gitignore.ignored(ignored_file) is True

    def test_detects_ignored_directory(self, tmp_path):
        subprocess.run(
            ["git", "init"],
            cwd=tmp_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        (tmp_path / ".gitignore").write_text("build/\n", encoding="utf-8")
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        gitignore = treex.GitIgnore(tmp_path)
        assert gitignore.ignored(build_dir) is True

    @patch("treex.subprocess.run")
    def test_git_not_installed(self, mock_run, tmp_path):
        mock_run.side_effect = FileNotFoundError
        gitignore = treex.GitIgnore(tmp_path)
        assert gitignore.enabled is False
        assert gitignore.ignored(tmp_path / "file.txt") is False


class TestPrintTree:
    def test_prints_files_and_directories(self, tmp_path, capsys):
        (tmp_path / "dir").mkdir()
        (tmp_path / "file.txt").write_text("hello", encoding="utf-8")
        stats = treex.print_tree(tmp_path)
        output = capsys.readouterr().out
        assert "dir" in output
        assert "file.txt" in output
        assert stats["directories"] == 1
        assert stats["files"] == 1
        assert stats["total_size"] == 5

    def test_summary_only_suppresses_tree(self, tmp_path, capsys):
        (tmp_path / "file.txt").write_text("hello", encoding="utf-8")
        stats = treex.print_tree(tmp_path, show_tree=False)
        output = capsys.readouterr().out
        assert output == ""
        assert stats["files"] == 1
        assert stats["total_size"] == 5

    def test_nested_directories(self, tmp_path, capsys):
        nested = tmp_path / "one" / "two"
        nested.mkdir(parents=True)
        (nested / "file.txt").write_text("hello", encoding="utf-8")
        stats = treex.print_tree(tmp_path)
        output = capsys.readouterr().out
        assert "one" in output
        assert "two" in output
        assert "file.txt" in output
        assert stats["directories"] == 2
        assert stats["files"] == 1

    def test_permission_denied(self, tmp_path, capsys):
        directory = tmp_path / "restricted"
        directory.mkdir()
        with patch.object(Path, "iterdir", side_effect=PermissionError):
            stats = treex.print_tree(directory)
        output = capsys.readouterr().out
        assert "[permission denied]" in output
        assert stats["directories"] == 0
        assert stats["files"] == 0

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

    @pytest.mark.skipif(sys.platform == "win32", reason="Not supported on Windows")
    def test_tree_entries_excludes_symlinks(self, tmp_path):
        target = tmp_path / "target.txt"
        target.touch()
        link = tmp_path / "link.txt"
        link.symlink_to(target)
        entries = treex._get_tree_entries(tmp_path, gitignore=None)
        assert [entry.name for entry in entries] == ["target.txt"]

    def test_collect_tree(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print('hello')\n", encoding="utf-8")
        (tmp_path / "README.md").write_text("# README\n", encoding="utf-8")
        stats = {"directories": 0, "files": 0, "total_size": 0}
        rows = []
        treex._collect_tree(tmp_path, "", stats, None, rows, False)
        assert [row[0] for row in rows] == [
            "├── src",
            "│   └── main.py",
            "└── README.md",
        ]
        assert stats["directories"] == 1
        assert stats["files"] == 2
        assert stats["total_size"] == (len("print('hello')\n") + len("# README\n"))

    def test_collect_tree_permission_denied(self, tmp_path):
        rows = []
        stats = {"directories": 0, "files": 0, "total_size": 0}

        with patch.object(Path, "iterdir", side_effect=PermissionError):
            treex._collect_tree(tmp_path, "", stats, None, rows, False)
        assert rows == [("└── [permission denied]", None)]
        assert stats["directories"] == 0
        assert stats["files"] == 0
        assert stats["total_size"] == 0

    def test_tree_name_width_aligns_file_metadata(self, tmp_path, capsys):
        (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
        (tmp_path / "long_filename.txt").write_text("hello", encoding="utf-8")
        treex.print_tree(tmp_path)
        lines = capsys.readouterr().out.splitlines()
        size_positions = [line.index("5 B") for line in lines if ".txt" in line]
        assert len(size_positions) == 2
        assert size_positions[0] == size_positions[1]


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


class TestArgumentParsing:
    def test_defaults(self):
        args = treex.parse_args([])
        assert args.directory == Path()
        assert args.all is False
        assert args.modified is False
        assert args.summary is False

    def test_directory(self):
        args = treex.parse_args(["/tmp/project"])
        assert args.directory == Path("/tmp/project")

    def test_all(self):
        args = treex.parse_args(["--all"])
        assert args.all is True

    def test_modified(self):
        args = treex.parse_args(["--modified"])
        assert args.modified is True

    def test_summary(self):
        args = treex.parse_args(["--summary"])
        assert args.summary is True

    def test_all_options(self):
        args = treex.parse_args(["--all", "--modified", "--summary", "/tmp/project"])
        assert args.directory == Path("/tmp/project")
        assert args.all is True
        assert args.modified is True
        assert args.summary is True

    def test_short_options(self):
        args = treex.parse_args(["-a", "-m", "-s"])
        assert args.all is True
        assert args.summary is True
        assert args.modified is True
