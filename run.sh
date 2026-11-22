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

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

echo "=== Stage 2: Specification Test ==="
"$PYTHON_CMD" src/main.py tests/spec_test.yaml "$TMP_DIR/spec.bin" --test

echo "=== Stage 3: Copy Array ==="
"$PYTHON_CMD" src/main.py tests/copy_array.yaml "$TMP_DIR/copy.bin"
"$PYTHON_CMD" src/interpreter.py \
    "$TMP_DIR/copy.bin" "$TMP_DIR/copy.xml" 200:204
cat "$TMP_DIR/copy.xml"

echo "=== Stage 4: ALU Unary Minus ==="
"$PYTHON_CMD" src/main.py tests/unary_minus_test.yaml "$TMP_DIR/alu.bin"
"$PYTHON_CMD" src/interpreter.py \
    "$TMP_DIR/alu.bin" "$TMP_DIR/alu.xml" 300:303
cat "$TMP_DIR/alu.xml"

for idx in 1 2 3; do
    echo "=== Stage 5: Vector Example $idx ==="
    "$PYTHON_CMD" src/main.py \
        "tests/vector_neg_${idx}.yaml" "$TMP_DIR/vec_${idx}.bin"
    "$PYTHON_CMD" src/interpreter.py \
        "$TMP_DIR/vec_${idx}.bin" "$TMP_DIR/vec_${idx}.xml" 300:308
    cat "$TMP_DIR/vec_${idx}.xml"
done