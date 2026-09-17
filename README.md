# treex

## Print a directory tree with file metadata

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

## Installation

Install `treex` from [PyPI][pypi-home] using either `pip` or `pipx`:

- `pip install treex-cli`
- `pipx install treex-cli`

----

## Usage

```
$ treex --help
usage: treex [-h] [-a] [-w N] [-m] [directory]

print a directory tree with file metadata.

positional arguments:
  directory       directory to scan (default: current directory)

options:
  -h, --help      show this help message and exit
  -a, --all       show all files, including ignored by git
  -w, --width N   starting column for file metadata (default: 50)
  -m, --modified  show file modification times
```

[github-profile]: https://github.com/cgoldberg
[github-repo]: https://github.com/cgoldberg/treex
[pypi-home]: https://pypi.org/project/treex-cli
[mit-license]: https://raw.githubusercontent.com/cgoldberg/treex/refs/heads/main/LICENSE
[tree-home]: https://oldmanprogrammer.net/source.php?dir=projects/tree
