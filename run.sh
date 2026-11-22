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

BIN_PATH="output.bin"
trap 'rm -f "$BIN_PATH"' EXIT

OUTPUT=$("$PYTHON_CMD" src/main.py tests/spec_test.yaml "$BIN_PATH" --test | tr -d '\r')
printf '%s\n' "$OUTPUT"

ACTUAL_SIZE=$(wc -c < "$BIN_PATH" | tr -d ' ')
if [ "$ACTUAL_SIZE" -ne 52 ]; then
    echo "Error: expected 52 bytes, got $ACTUAL_SIZE bytes." >&2
    exit 1
fi

EXPECTED_HEX=$(cat <<'EOF'
0x6F, 0x7B, 0x01, 0x00, 0x80, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
0x11, 0xC3, 0x00, 0x00, 0x28, 0x1E, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
0x2E, 0x72, 0x01, 0x00, 0xE0, 0x1C, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
0x57, 0x7F, 0x01, 0x00, 0x38, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
EOF
)

ACTUAL_HEX=$(printf '%s\n' "$OUTPUT" | tail -n +2)
if [ "$ACTUAL_HEX" != "$EXPECTED_HEX" ]; then
    echo "Stage 2 test failed: byte sequences do not match specification." >&2
    exit 1
fi

echo "Stage 2 test passed."