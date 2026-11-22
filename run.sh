#!/usr/bin/env bash
set -e

if [ "$#" -eq 0 ]; then
    python src/main.py tests/spec_test.yaml output.bin --test
else
    python src/main.py "$@"
fi