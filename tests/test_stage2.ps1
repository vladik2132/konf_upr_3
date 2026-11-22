$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

$pythonCmd = if (Test-Path ".\.venv\Scripts\python.exe") {
    ".\.venv\Scripts\python.exe"
} else {
    "python"
}

$binPath = "output.bin"
$expectedHex = @(
    "0x6F, 0x7B, 0x01, 0x00, 0x80, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00",
    "0x11, 0xC3, 0x00, 0x00, 0x28, 0x1E, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00",
    "0x2E, 0x72, 0x01, 0x00, 0xE0, 0x1C, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00",
    "0x57, 0x7F, 0x01, 0x00, 0x38, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00"
)

try {
    $output = @(& $pythonCmd src/main.py tests/spec_test.yaml $binPath --test)
    foreach ($line in $output) {
        Write-Host $line
    }

    if (-not (Test-Path $binPath)) {
        Write-Error "Binary file was not created."
        exit 1
    }

    $actualSize = (Get-Item $binPath).Length
    if ($actualSize -ne 52) {
        Write-Error "Expected 52 bytes, got $actualSize bytes."
        exit 1
    }

    if ($output.Count -ne 5 -or ($output[0] -notmatch "\b52\b")) {
        Write-Error "Missing or invalid binary size output line."
        exit 1
    }

    $actualHex = $output[1..4] -join "`n"
    if ($actualHex -ne ($expectedHex -join "`n")) {
        Write-Error "Stage 2 test failed: byte sequences do not match specification."
        exit 1
    }

    Write-Host "Stage 2 test passed."
}
finally {
    if (Test-Path $binPath) {
        Remove-Item $binPath -Force
    }
}