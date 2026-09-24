# treex

## List directory contents as a tree with file and directory metadata

- Copyright (c) 2026 [Corey Goldberg][github-profile]
- Development: [GitHub][github-repo]
- Releases: [PyPI][pypi-home]
- License: [MIT][mit-license]

----

## About

`treex` is a command-line utility that recursively scans a directory and
lists its contents as a tree along with file and directory metadata.

- Shows human-readable file sizes
- Shows recursive directory sizes
- Shows line counts for text files
- Identifies binary and unreadable files by type
- Optionally shows modification timestamps
- Respects `.gitignore` rules when Git is installed

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

## Requirements

- Python 3.10+
- Git 2.0+ (optional)
- UTF-8-compatible terminal

----

## Installation

Install `treex` from [PyPI][pypi-home] using either `pip` or `pipx`:

- `pip install treex-cli`
- `pipx install treex-cli`

----

## Usage

```
$ treex --help
usage: treex [-h] [-a] [-m] [-q] [-s] [directory]

List directory contents as a tree with file and directory metadata.

positional arguments:
  directory       directory to scan (default: current directory)

options:
  -h, --help      show this help message and exit
  -a, --all       show all files (including those ignored by Git)
  -m, --modified  show file modification times
  -q, --quiet     don't show file metadata
  -s, --summary   show summary only
```

----

## Screenshot

![Screenshot](https://raw.githubusercontent.com/cgoldberg/treex/refs/heads/main/screenshot.png)

[github-profile]: https://github.com/cgoldberg
[github-repo]: https://github.com/cgoldberg/treex
[pypi-home]: https://pypi.org/project/treex-cli
[mit-license]: https://raw.githubusercontent.com/cgoldberg/treex/refs/heads/main/LICENSE
