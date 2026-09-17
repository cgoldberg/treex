# Copyright (c) 2026 Corey Goldberg
# SPDX-License-Identifier: MIT


"""Tests for treex."""

import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import treex


class TestFormatSize:
    def test_bytes(self):
        assert treex.format_size(0) == "0 B"
        assert treex.format_size(512) == "512 B"
        assert treex.format_size(1023) == "1023 B"

    def test_kilobytes(self):
        assert treex.format_size(1024) == "1.0 KB"
        assert treex.format_size(1536) == "1.5 KB"

    def test_megabytes(self):
        assert treex.format_size(1024 * 1024) == "1.0 MB"
        assert treex.format_size(5 * 1024 * 1024) == "5.0 MB"

    def test_gigabytes(self):
        assert treex.format_size(1024**3) == "1.0 GB"

    def test_large_values(self):
        assert treex.format_size(1024**4) == "1.0 TB"


class TestFormatModified:
    def test_timestamp(self):
        timestamp = datetime(2026, 9, 16, 14, 32).timestamp()
        assert treex.format_modified(timestamp) == "2026-09-16 14:32"


class TestIsBinaryFile:
    def test_empty_file_is_not_binary(self, tmp_path):
        path = tmp_path / "empty"
        path.write_bytes(b"")
        assert treex.is_binary_file(path) is False

    def test_text_file_is_not_binary(self, tmp_path):
        path = tmp_path / "hello.txt"
        path.write_text("Hello, world!\nThis is text.\n")
        assert treex.is_binary_file(path) is False

    def test_utf8_file_is_not_binary(self, tmp_path):
        path = tmp_path / "unicode.txt"
        path.write_text("Hello 🌎\nCafé\n日本語\n")
        assert treex.is_binary_file(path) is False

    def test_null_byte_is_binary(self, tmp_path):
        path = tmp_path / "binary"
        path.write_bytes(b"hello\x00world")

        assert treex.is_binary_file(path) is True

    def test_invalid_utf8_is_binary(self, tmp_path):
        path = tmp_path / "binary"
        path.write_bytes(b"\xff\xfe\xfd")
        assert treex.is_binary_file(path) is True

    def test_missing_file_is_binary(self, tmp_path):
        path = tmp_path / "does-not-exist"
        assert treex.is_binary_file(path) is True


class TestCountLines:
    def test_empty_file(self, tmp_path):
        path = tmp_path / "empty"
        path.write_bytes(b"")
        assert treex.count_lines(path) == 0

    def test_single_line_with_newline(self, tmp_path):
        path = tmp_path / "file.txt"
        path.write_text("hello\n")
        assert treex.count_lines(path) == 1

    def test_multiple_lines(self, tmp_path):
        path = tmp_path / "file.txt"
        path.write_text("one\ntwo\nthree\n")
        assert treex.count_lines(path) == 3

    def test_last_line_without_newline(self, tmp_path):
        path = tmp_path / "file.txt"
        path.write_text("one\ntwo\nthree")
        assert treex.count_lines(path) == 3

    def test_missing_file(self, tmp_path):
        path = tmp_path / "does-not-exist"
        assert treex.count_lines(path) is None


class TestFileInfo:
    def test_text_file(self, tmp_path):
        path = tmp_path / "file.txt"
        path.write_text("one\ntwo\nthree\n")
        size, info, raw_size, modified = treex.file_info(path)
        assert size == "14 B"
        assert info == "3 lines"
        assert raw_size == 14
        assert modified is not None

    def test_binary_file(self, tmp_path):
        path = tmp_path / "image.bin"
        contents = b"\x00\x01\x02\x03"
        path.write_bytes(contents)
        size, info, raw_size, modified = treex.file_info(path)
        assert size == "4 B"
        assert info == "[binary]"
        assert raw_size == 4
        assert modified is not None

    def test_empty_file(self, tmp_path):
        path = tmp_path / "empty.txt"
        path.write_bytes(b"")
        size, info, raw_size, modified = treex.file_info(path)
        assert size == "0 B"
        assert info == "0 lines"
        assert raw_size == 0
        assert modified is not None

    def test_missing_file(self, tmp_path):
        path = tmp_path / "missing.txt"
        size, info, raw_size, modified = treex.file_info(path)
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
        (tmp_path / "ignored.txt").write_text("ignored")
        (tmp_path / "README.md").write_text("hello")
        (tmp_path / ".gitignore").write_text("ignored.txt\n")
        gitignore = treex.GitIgnore(tmp_path)
        treex.print_tree(tmp_path, gitignore=gitignore)
        output = capsys.readouterr().out
        assert not self.has_entry(output, ".git")
        assert self.has_entry(output, ".gitignore")
        assert not self.has_entry(output, "ignored.txt")
        assert self.has_entry(output, "README.md")

    def test_disabled_shows_everything(self, tmp_path, capsys):
        self.init_git_repo(tmp_path)
        (tmp_path / "ignored.txt").write_text("ignored")
        (tmp_path / "README.md").write_text("hello")
        (tmp_path / ".gitignore").write_text("ignored.txt\n")
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
        (tmp_path / ".gitignore").write_text("*.log\n")
        normal_file = tmp_path / "README.md"
        normal_file.write_text("hello")
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
        (tmp_path / ".gitignore").write_text("*.log\n")
        ignored_file = tmp_path / "debug.log"
        ignored_file.write_text("debug output")
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
        (tmp_path / ".gitignore").write_text("build/\n")
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
        (tmp_path / "file.txt").write_text("hello")
        stats = treex.print_tree(tmp_path)
        output = capsys.readouterr().out
        assert "dir" in output
        assert "file.txt" in output
        assert stats["directories"] == 1
        assert stats["files"] == 1
        assert stats["total_size"] == 5

    def test_summary_only_suppresses_tree(self, tmp_path, capsys):
        (tmp_path / "file.txt").write_text("hello")
        stats = treex.print_tree(tmp_path, show_tree=False)
        output = capsys.readouterr().out
        assert output == ""
        assert stats["files"] == 1
        assert stats["total_size"] == 5

    def test_nested_directories(self, tmp_path, capsys):
        nested = tmp_path / "one" / "two"
        nested.mkdir(parents=True)
        (nested / "file.txt").write_text("hello")
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


class TestArgumentParsing:
    def test_defaults(self):
        args = treex.parse_args([])
        assert args.directory == Path()
        assert args.all is False
        assert args.modified is False
        assert args.summary is False
        assert args.width == 50

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

    def test_width(self):
        args = treex.parse_args(["--width", "100"])
        assert args.width == 100

    def test_all_options(self):
        args = treex.parse_args(
            ["--all", "--modified", "--summary", "--width", "100", "/tmp/project"]
        )
        assert args.directory == Path("/tmp/project")
        assert args.all is True
        assert args.modified is True
        assert args.summary is True
        assert args.width == 100

    def test_short_options(self):
        args = treex.parse_args(["-a", "-m", "-s", "-w", "100"])
        assert args.all is True
        assert args.summary is True
        assert args.modified is True
        assert args.width == 100
