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

- Respects `.gitignore` rules inside Git repositories
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
- UTF-8-compatible terminal

----

## Git ignore support

`treex` uses [Gitoxide][gitoxide-home] (`gix`), a native Rust implementation of
Git functionality, to evaluate `.gitignore` rules without invoking the Git
executable. Git does not need to be installed for ignore matching to work.

When the specified directory is inside a Git working tree, `treex` respects
applicable `.gitignore` rules by default. Outside a Git working tree, Git ignore
filtering is disabled. Use `--all` to include files ignored by Git.

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
usage: treex [-h] [-V] [-a] [-m] [-q] [-d] [-s] [-i PATTERN] [-e PATTERN]
             [-I PATTERN] [-E PATTERN] [-D DEPTH]
             [directory]

List directory contents as a tree with file and directory metadata.

positional arguments:
  directory                    directory to scan (default: current directory)

options:
  -h, --help                   show this help message and exit
  -V, --version                show version information and exit
  -a, --all                    show all files, including those ignored by Git
  -m, --modified               show file modification times
  -q, --quiet                  don't show file metadata
  -d, --dirs                   show directories only
  -s, --summary                show summary only
  -i, --include PATTERN        include paths matching a glob pattern
  -e, --exclude PATTERN        exclude paths matching a glob pattern
  -I, --include-regex PATTERN  include paths matching a regular expression
  -E, --exclude-regex PATTERN  exclude paths matching a regular expression
  -D, --depth DEPTH            limit levels displayed below starting directory
```

### Filtering paths

Use `--include` and `--exclude` to filter paths by glob pattern:

```
treex --include '*.py'
treex --exclude 'tests/*.py'
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

----

## Screenshot

![Screenshot](https://raw.githubusercontent.com/cgoldberg/treex/refs/heads/main/screenshot.png)

[github-profile]: https://github.com/cgoldberg
[github-repo]: https://github.com/cgoldberg/treex
[gitoxide-home]: https://rustutils.com/tools/gitoxide
[mit-license]: https://raw.githubusercontent.com/cgoldberg/treex/refs/heads/main/LICENSE
[pypi-home]: https://pypi.org/project/treex-cli
