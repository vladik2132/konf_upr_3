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
COPY_DUMP="dump_stage3.xml"
ALU_BIN="unary_minus.bin"
ALU_DUMP="dump_stage4.xml"
trap 'rm -f "$SPEC_BIN" "$COPY_BIN" "$COPY_DUMP" "$ALU_BIN" "$ALU_DUMP"' EXIT

"$PYTHON_CMD" src/main.py tests/spec_test.yaml "$SPEC_BIN" --test

"$PYTHON_CMD" src/main.py tests/copy_array.yaml "$COPY_BIN"
"$PYTHON_CMD" src/interpreter.py "$COPY_BIN" "$COPY_DUMP" 200:204
cat "$COPY_DUMP"

"$PYTHON_CMD" src/main.py tests/unary_minus_test.yaml "$ALU_BIN"
"$PYTHON_CMD" src/interpreter.py "$ALU_BIN" "$ALU_DUMP" 300:303
cat "$ALU_DUMP"