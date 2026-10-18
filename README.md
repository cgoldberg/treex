# treex

## List directory contents as a tree with file and directory metadata

- Copyright (c) 2026 [Corey Goldberg][github-profile]
- Development: [GitHub][github-repo]
- Releases: [PyPI][pypi-home]
- License: [MIT][mit-license]

----

## About

`treex` is a command-line utility that recursively scans a directory and lists
its contents as a tree along with file and directory metadata.

Features:

- Respects `.gitignore` rules when Git is installed
- Shows human-readable file sizes
- Shows recursive directory sizes
- Shows line counts for text files
- Identifies binary and unreadable files by type
- Optionally shows modification timestamps
- Optionally includes or excludes files using glob patterns
- Optionally limits the depth of the displayed tree

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
usage: treex [-h] [--all] [--modified] [--quiet] [--dirs] [--summary]
             [--include PATTERN] [--exclude PATTERN] [--depth DEPTH]
             [directory]

List directory contents as a tree with file and directory metadata.

positional arguments:
  directory              directory to scan (default: current directory)

options:
  -h, --help             show this help message and exit
  --all, -a              show all files, including those ignored by Git
  --modified, -m         show file modification times
  --quiet, -q            don't show file metadata
  --dirs, -d             show directories only
  --summary, -s          show summary only
  --include, -i PATTERN  include files matching a glob pattern
  --exclude, -e PATTERN  exclude files matching a glob pattern
  --depth, -D DEPTH      limit levels displayed below the starting directory
```

### Filtering files

Use `--include` to display only files that match a glob pattern:

```
treex --include '*.py'
```

Use `--exclude` to hide files that match a glob pattern:

```
treex --exclude '*.pyc'
```

Patterns match filenames only, regardless of their location in the directory
tree. Matching is case-sensitive. When both options are provided, exclusions
take precedence over inclusions.

For example:

```
treex --include '.py' --exclude 'test_.py'
```

This displays Python files except those whose filenames begin with `test_`.

Note: quote glob patterns to prevent the shell from expanding them before
`treex` receives them.

### Limiting tree depth

Use `--depth` (or `-D`) to limit how many levels below the starting directory
are displayed:

```
treex --depth 3
```

The depth must be at least 1.

Directory sizes and summary totals reflect only files within the limit that pass
the include/exclude filters.

----

## Screenshot

![Screenshot](https://raw.githubusercontent.com/cgoldberg/treex/refs/heads/main/screenshot.png)

----

[github-profile]: https://github.com/cgoldberg
[github-repo]: https://github.com/cgoldberg/treex
[pypi-home]: https://pypi.org/project/treex-cli
[mit-license]: https://raw.githubusercontent.com/cgoldberg/treex/refs/heads/main/LICENSE
