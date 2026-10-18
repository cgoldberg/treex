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

### Features:

- Respects `.gitignore` rules when Git is installed
- Shows human-readable file sizes
- Shows recursive directory sizes
- Shows line counts for text files
- Identifies binary and unreadable files by type
- Optionally shows modification timestamps
- Optionally includes or excludes paths using glob patterns
- Optionally includes or excludes paths using regular expressions
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

Install `treex` from [PyPI][pypi-home] using your preferred Python package
manager:

- **pip**: `pip install treex-cli`
- **pipx**: `pipx install treex-cli`
- **uv**: `uv tool install treex-cli`

----

## Usage

```
usage: treex [-h] [--all] [--modified] [--quiet] [--dirs] [--summary]
             [--include PATTERN] [--exclude PATTERN] [--include-regex PATTERN]
             [--exclude-regex PATTERN] [--depth DEPTH]
             [directory]

List directory contents as a tree with file and directory metadata.

positional arguments:
  directory                    directory to scan (default: current directory)

options:
  -h, --help                   show this help message and exit
  --all, -a                    show all files, including those ignored by Git
  --modified, -m               show file modification times
  --quiet, -q                  don't show file metadata
  --dirs, -d                   show directories only
  --summary, -s                show summary only
  --include, -i PATTERN        include paths matching a glob pattern
  --exclude, -e PATTERN        exclude paths matching a glob pattern
  --include-regex, -I PATTERN  include paths matching a regular expression
  --exclude-regex, -E PATTERN  exclude paths matching a regular expression
  --depth, -D DEPTH            limit levels displayed below the starting directory
```

### Filtering paths

Use `--include` and `--exclude` to filter paths by glob pattern:

```
treex --include '*.py'
treex --exclude '*.pyc'
treex --include '*.py' --exclude 'test_*.py'
```

Use `--include-regex` and `--exclude-regex` to filter paths by regular
expression:

```
treex --include-regex '^src/'
treex --exclude-regex '(^|/)tests/'
treex --include-regex '\.py$' --exclude-regex '(^|/)test_[^/]*\.py$'
```

Patterns match paths relative to the starting directory, using forward slashes
as separators. Matching is case-sensitive. Glob patterns use `*` to match any
characters, including directory separators. Regular expressions use Python's
regex syntax. Exclusions take precedence over inclusions.

Note: quote glob and regex patterns to prevent the shell from interpreting them
before `treex` receives them.

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

[github-profile]: https://github.com/cgoldberg
[github-repo]: https://github.com/cgoldberg/treex
[mit-license]: https://raw.githubusercontent.com/cgoldberg/treex/refs/heads/main/LICENSE
[pypi-home]: https://pypi.org/project/treex-cli
