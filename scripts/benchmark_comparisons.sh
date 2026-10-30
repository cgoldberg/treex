#!/usr/bin/env bash
#
# Benchmarks multiple treex releases

# Uses isolated, version-specific environments via pipx run and hyperfine
# to measure execution times.
#
# Configuration:
#   RUNS          Number of benchmark runs per command.
#   VERSION_LIMIT Maximum number of treex-cli releases to test (0 = all).
#   DATA_DIR      Root directory of the filesystem snapshot.
#
# Historical versions are tested without replacing the globally installed
# treex-cli.
#
# Stage data with:
#
#   rsync -av \
#     --exclude='/treex_dataset/***' \
#     --exclude='/Downloads/***' \
#     --exclude='/.local/share/containers/***' \
#     ~/ ~/treex_dataset/home_snapshot/

set -Eeuo pipefail

RUNS=3
VERSION_LIMIT=2 # use 0 for all
DATA_DIR="${HOME}/treex_dataset/home_snapshot"

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
REPO_ROOT="$(git -C "${SCRIPT_DIR}" rev-parse --show-toplevel)"

DATASAET_DIRS=(
    "${DATA_DIR}/code"
    "${DATA_DIR}/"
)

setup() {
    echo
    echo "============================================================"
    echo "  TREEX BENCHMARK SUITE"
    echo "============================================================"
    echo "Dataset:  ${DATA_DIR}"
    echo "Runs:     ${RUNS}"
    echo "Started:  $(date)"
    echo
    echo ">>> Preparing benchmark environment..."
    pipx uninstall treex-cli >/dev/null 2>&1 || true
    pipx install treex-cli --upgrade --force
    cd "${DATA_DIR}"
    echo ">>> Setup complete."
}

benchmark_versions() {
    echo
    echo "============================================================"
    echo "  PHASE 2: TREEX VERSION COMPARISON"
    echo "============================================================"
    echo "Testing repository tags from newest to oldest."
    echo
    local -a tags
    mapfile -t tags < <(
        git -C "${REPO_ROOT}" tag --sort=-version:refname |
        { if (( VERSION_LIMIT > 0 )); then head -n "${VERSION_LIMIT}"; else cat; fi; }
    )
    for tag in "${tags[@]}"; do
        echo
        echo
        echo "============================================================"
        echo "  VERSION: ${tag}"
        echo "============================================================"
        for d in "${DATASAET_DIRS[@]}"; do
            echo "--- ${tag} | ${d} | gitignore filtering ---"
            hyperfine --warmup 1 --runs "${RUNS}" \
                "pipx run --spec 'treex-cli==${tag}' treex '${d}'" \
                "pipx run --spec 'treex-cli==${tag}' treex -q '${d}'"
            echo "--- ${tag} | ${d} | all entries ---"
            hyperfine --warmup 1 --runs "${RUNS}" \
                "pipx run --spec 'treex-cli==${tag}' treex -a '${d}'" \
                "pipx run --spec 'treex-cli==${tag}' treex -q -a '${d}'"
            echo
        done
    done
    echo
    echo
    echo ">>> Version comparison complete."
}

echo
echo "Benchmark suite starting..."
echo

setup
benchmark_versions

echo
echo
echo "============================================================"
echo "  ALL BENCHMARKS COMPLETE"
echo "============================================================"
echo "Finished: $(date)"
