# treex

## Print a directory tree with file metadata

`treex` is a command-line utility (similar to [tree][tree-home]) that
recursively scans a directory and prints a tree with file names, sizes, line
counts, and modification times. It runs on Python, requires Git, and respects
`.gitignore` rules.

- Copyright (c) 2026 [Corey Goldberg][github-profile]
- Development: [GitHub][github-repo]
- Releases: [PyPI][pypi-home]
- License: [MIT][mit-license]

----

### Installation

Install the package from [PyPI][pypi-home]:

```
pip install talend-task
```
----

### CLI Options:

```
$ treex --help
usage: treex [-h] [-a] [-w N] [-m] [directory]

Print a directory tree with file metadata.

positional arguments:
  directory       directory to scan (default: current directory)

options:
  -h, --help      show this help message and exit
  -a, --all       show all files, including git-ignored
  -w, --width N   starting column for file metadata (default: 50)
  -m, --modified  show file modification times
```

[github-profile]: https://github.com/cgoldberg
[github-repo]: https://github.com/cgoldberg/treex
[pypi-home]: https://pypi.org/project/treex-cli
[mit-license]: https://raw.githubusercontent.com/cgoldberg/treex/refs/heads/main/LICENSE
[tree-home]: https://oldmanprogrammer.net/source.php?dir=projects/tree
