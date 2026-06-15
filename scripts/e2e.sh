#!/usr/bin/env bash
# Smoke test for jg-lint built-in rules.
#
# For every directory under examples/, runs `jg-lint check` against that
# directory using its own pyproject.toml. Expects:
#   - files named bad*.py to be reported with the rule code matching the
#     directory name and the CLI to exit non-zero
#   - files named good*.py to never appear in the output and the CLI to
#     exit zero when only good files are linted
#
# Usage: scripts/e2e.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EXAMPLES="$ROOT/examples"

if ! command -v jg-lint >/dev/null 2>&1; then
    echo "jg-lint not on PATH. Build/install it first (e.g. 'uv run maturin develop')." >&2
    exit 2
fi

if [ ! -d "$EXAMPLES" ]; then
    echo "No examples directory at $EXAMPLES" >&2
    exit 2
fi

fail=0
for example in "$EXAMPLES"/*/; do
    rule="$(basename "$example")"
    echo "==> $rule"

    bad_files=()
    while IFS= read -r f; do bad_files+=("$f"); done < <(find "$example" -type f -name 'bad*.py')
    good_files=()
    while IFS= read -r f; do good_files+=("$f"); done < <(find "$example" -type f -name 'good*.py')

    if [ ${#bad_files[@]} -eq 0 ]; then
        echo "  FAIL: no bad*.py fixtures in $example"
        fail=1
        continue
    fi

    bad_output=$(jg-lint check --config "$example" "${bad_files[@]}" 2>&1)
    bad_exit=$?

    if [ "$bad_exit" -eq 0 ]; then
        echo "  FAIL: linting bad fixtures exited 0, expected non-zero"
        echo "$bad_output" | sed 's/^/    /'
        fail=1
    fi
    if ! echo "$bad_output" | grep -q "$rule"; then
        echo "  FAIL: rule code $rule not present in output for bad fixtures"
        echo "$bad_output" | sed 's/^/    /'
        fail=1
    fi
    for bf in "${bad_files[@]}"; do
        if ! echo "$bad_output" | grep -Fq "$bf"; then
            echo "  FAIL: $bf not flagged"
            fail=1
        fi
    done

    if [ ${#good_files[@]} -gt 0 ]; then
        good_output=$(jg-lint check --config "$example" "${good_files[@]}" 2>&1)
        good_exit=$?
        if [ "$good_exit" -ne 0 ]; then
            echo "  FAIL: linting good fixtures exited $good_exit, expected 0"
            echo "$good_output" | sed 's/^/    /'
            fail=1
        fi
        if echo "$good_output" | grep -q "$rule"; then
            echo "  FAIL: rule code $rule reported against good fixtures"
            echo "$good_output" | sed 's/^/    /'
            fail=1
        fi
    fi
done

if [ "$fail" -eq 0 ]; then
    echo "e2e: all examples passed"
fi
exit "$fail"
