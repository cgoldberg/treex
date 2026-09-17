# treex

## List directory contents in a tree format with file metadata.

- Copyright (c) 2026 [Corey Goldberg][github-profile]
- Development: [GitHub][github-repo]
- Releases: [PyPI][pypi-home]
- License: [MIT][mit-license]

----

## About

`treex` is a command-line utility (similar to [tree][tree-home]) that recursively
scans a directory and prints its contents as a tree using Unicode box-drawing
characters. File names include their human-readable size and, optionally,
modification time. Text files also include their line count, while binary and
unreadable files are marked with their type. When Git is installed, it respects
`.gitignore` rules.

Requirements:

- Python 3.10+
- Git 2.0+ (optional)
- UTF-8-compatible terminal

----

## Status

<table>
  <tr>
    <td>Latest Version</td>
    <td>
      <a href="https://pypi.org/project/treex-cli">
        <img src="https://img.shields.io/pypi/v/treex-cli.svg">
      </a>
    </td>
  </tr>
  <tr>
    <td>Tests (CI)</td>
    <td>
      <a href="https://github.com/cgoldberg/treex/actions/workflows/test.yml">
        <img src="https://github.com/cgoldberg/treex/actions/workflows/test.yml/badge.svg">
      </a>
    </td>
  </tr>
  <tr>
    <td>Supported Python Versions</td>
    <td>
      <a href="https://pypi.org/project/treex-cli">
        <img src="https://img.shields.io/pypi/pyversions/treex-cli">
      </a>
    </td>
  </tr>
</table>

----

## Installation

Install `treex` from [PyPI][pypi-home] using either `pip` or `pipx`:

- `pip install treex-cli`
- `pipx install treex-cli`

----

## Usage

```
$ treex --help
usage: treex [-h] [-a] [-m] [-s] [-w N] [directory]

List directory contents in a tree format with file metadata.

positional arguments:
  directory       directory to scan (default: current directory)

options:
  -h, --help      show this help message and exit
  -a, --all       show all files, including ignored by git
  -m, --modified  show file modification times
  -s, --summary   show summary only
  -w, --width N   starting column for file metadata (default: 50)
```

----

## Screenshot

![Screenshot](https://raw.githubusercontent.com/cgoldberg/treex/refs/heads/main/screenshot.png)

[github-profile]: https://github.com/cgoldberg
[github-repo]: https://github.com/cgoldberg/treex
[pypi-home]: https://pypi.org/project/treex-cli
[mit-license]: https://raw.githubusercontent.com/cgoldberg/treex/refs/heads/main/LICENSE
[tree-home]: https://oldmanprogrammer.net/source.php?dir=projects/tree
