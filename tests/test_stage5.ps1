$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

$pythonCmd = if (Test-Path ".\.venv\Scripts\python.exe") {
    ".\.venv\Scripts\python.exe"
} else {
    "python"
}

function Assert-XmlRange {
    param(
        [string]$DumpPath,
        [int]$StartAddr,
        [string[]]$ExpectedValues
    )
    if (-not (Test-Path $DumpPath)) {
        Write-Error "XML dump file was not created: $DumpPath"
        exit 1
    }
    $xmlText = Get-Content $DumpPath -Raw -Encoding UTF8
    [xml]$doc = $xmlText
    $cells = @($doc.memory.cell)
    if ($cells.Count -ne $ExpectedValues.Count) {
        Write-Error "Unexpected cell count in $DumpPath."
        exit 1
    }
    for ($i = 0; $i -lt $ExpectedValues.Count; $i++) {
        $expectedAddr = [string]($StartAddr + $i)
        $actualAddr = $cells[$i].address
        $actualVal = $cells[$i].InnerText
        if ($actualAddr -ne $expectedAddr -or
            $actualVal -ne $ExpectedValues[$i]) {
            Write-Error (
                "Mismatch at addr=$actualAddr : " +
                "got $actualVal, expected $($ExpectedValues[$i])."
            )
            exit 1
        }
    }
    return $xmlText
}

function Test-VectorCase {
    param(
        [string]$CaseName,
        [string]$YamlPath,
        [string[]]$ExpectedSrc,
        [string[]]$ExpectedDst
    )
    $binPath = "${CaseName}.bin"
    $srcDump = "${CaseName}_src.xml"
    $dstDump = "${CaseName}_dst.xml"
    try {
        Write-Host "=== $CaseName ==="
        & $pythonCmd src/main.py $YamlPath $binPath
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Assembler failed on $YamlPath."
            exit 1
        }

        & $pythonCmd src/interpreter.py $binPath $srcDump 100:108
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Interpreter failed (src) on $YamlPath."
            exit 1
        }
        $null = Assert-XmlRange -DumpPath $srcDump `
            -StartAddr 100 -ExpectedValues $ExpectedSrc

        & $pythonCmd src/interpreter.py $binPath $dstDump 300:308
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Interpreter failed (dst) on $YamlPath."
            exit 1
        }
        $dstXml = Assert-XmlRange -DumpPath $dstDump `
            -StartAddr 300 -ExpectedValues $ExpectedDst
        Write-Host $dstXml
    }
    finally {
        foreach ($tmpFile in @($binPath, $srcDump, $dstDump)) {
            if (Test-Path $tmpFile) {
                Remove-Item $tmpFile -Force
            }
        }
    }
}

Test-VectorCase `
    -CaseName "vector_neg_1" `
    -YamlPath "tests/vector_neg_1.yaml" `
    -ExpectedSrc @("1", "2", "3", "4", "5", "6", "7", "8", "9") `
    -ExpectedDst @("-1", "-2", "-3", "-4", "-5", "-6", "-7", "-8", "-9")

Test-VectorCase `
    -CaseName "vector_neg_2" `
    -YamlPath "tests/vector_neg_2.yaml" `
    -ExpectedSrc @(
        "0", "100", "255", "1024", "4096",
        "8192", "12000", "16383", "0"
    ) `
    -ExpectedDst @(
        "0", "-100", "-255", "-1024", "-4096",
        "-8192", "-12000", "-16383", "0"
    )

Test-VectorCase `
    -CaseName "vector_neg_3" `
    -YamlPath "tests/vector_neg_3.yaml" `
    -ExpectedSrc @(
        "-50", "0", "15", "-300", "7",
        "-999", "1", "-42", "88"
    ) `
    -ExpectedDst @(
        "50", "0", "-15", "300", "-7",
        "999", "-1", "42", "-88"
    )

Write-Host "Stage 5 tests passed (all 3 vector examples verified)."