$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

$output = python src/main.py tests/spec_test.yaml output.bin --test
$output | ForEach-Object { Write-Host $_ }

$expected = @(
    "A=111, B=758, C=112",
    "A=17, B=390, C=965",
    "A=46, B=740, C=924",
    "A=87, B=766, C=7"
)

if (($output -join "`n") -ne ($expected -join "`n")) {
    Write-Error "Stage 1 test failed: output does not match specification."
    exit 1
}

Write-Host "Stage 1 test passed."