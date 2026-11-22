#!/usr/bin/env bash
set -euo pipefail

if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

if [ "$#" -gt 0 ]; then
    "$PYTHON_CMD" src/main.py "$@"
    exit 0
fi

SPEC_BIN="output.bin"
COPY_BIN="copy_array.bin"
DUMP_XML="dump_stage3.xml"
trap 'rm -f "$SPEC_BIN" "$COPY_BIN" "$DUMP_XML"' EXIT

"$PYTHON_CMD" src/main.py tests/spec_test.yaml "$SPEC_BIN" --test
"$PYTHON_CMD" src/main.py tests/copy_array.yaml "$COPY_BIN"
"$PYTHON_CMD" src/interpreter.py "$COPY_BIN" "$DUMP_XML" 200:204
cat "$DUMP_XML"