$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

$pythonCmd = if (Test-Path ".\.venv\Scripts\python.exe") {
    ".\.venv\Scripts\python.exe"
} else {
    "python"
}

$binPath = "unary_minus.bin"
$dumpPath = "dump_stage4.xml"
$expectedValues = @("-42", "0", "-1234", "42")

try {
    & $pythonCmd src/main.py tests/unary_minus_test.yaml $binPath
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Assembler failed."
        exit 1
    }

    & $pythonCmd src/interpreter.py $binPath $dumpPath 300:303
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Interpreter failed."
        exit 1
    }

    if (-not (Test-Path $dumpPath)) {
        Write-Error "XML dump file was not created."
        exit 1
    }

    $xmlText = Get-Content $dumpPath -Raw -Encoding UTF8
    Write-Host $xmlText

    [xml]$doc = $xmlText
    $cells = @($doc.memory.cell)
    if ($cells.Count -ne $expectedValues.Count) {
        Write-Error "Unexpected cell count in XML dump."
        exit 1
    }

    for ($i = 0; $i -lt $expectedValues.Count; $i++) {
        $expectedAddr = [string](300 + $i)
        $actualAddr = $cells[$i].address
        $actualVal = $cells[$i].InnerText
        if ($actualAddr -ne $expectedAddr -or $actualVal -ne $expectedValues[$i]) {
            Write-Error "Mismatch at index $i : got addr=$actualAddr val=$actualVal."
            exit 1
        }
    }

    Write-Host "Stage 4 test passed."
}
finally {
    if (Test-Path $binPath) {
        Remove-Item $binPath -Force
    }
    if (Test-Path $dumpPath) {
        Remove-Item $dumpPath -Force
    }
}