param(
    [switch]$SkipInstaller,
    [string]$PythonExe = "",
    [string]$SignToolPath = "",
    [string]$CertificateThumbprint = "",
    [string]$CertificatePfxPath = "",
    [string]$TimestampUrl = "http://timestamp.digicert.com",
    [switch]$RequireSignature
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Version = (Get-Content (Join-Path $Root "VERSION") -Raw).Trim()
$EnvFile = Join-Path $Root ".env"
$GeneratedDir = Join-Path $Root "installer\generated"
$PublicConfig = Join-Path $GeneratedDir "prontu_public.env"
$SigningEnabled = (
    -not [string]::IsNullOrWhiteSpace($CertificateThumbprint) -or
    -not [string]::IsNullOrWhiteSpace($CertificatePfxPath)
)

if (
    -not [string]::IsNullOrWhiteSpace($CertificateThumbprint) -and
    -not [string]::IsNullOrWhiteSpace($CertificatePfxPath)
) {
    throw "Informe somente CertificateThumbprint ou CertificatePfxPath, nunca os dois."
}
if ($RequireSignature -and -not $SigningEnabled) {
    throw "Assinatura obrigatoria, mas nenhum certificado foi informado."
}

function Find-SignTool {
    if (-not [string]::IsNullOrWhiteSpace($SignToolPath)) {
        if (-not (Test-Path -LiteralPath $SignToolPath)) {
            throw "SignTool nao encontrado no caminho informado: $SignToolPath"
        }
        return (Resolve-Path -LiteralPath $SignToolPath).Path
    }

    $WindowsKits = "C:\Program Files (x86)\Windows Kits\10\bin"
    if (Test-Path -LiteralPath $WindowsKits) {
        $Found = Get-ChildItem -LiteralPath $WindowsKits -Filter "signtool.exe" -Recurse -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match '\\x64\\signtool\.exe$' } |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($Found) {
            return $Found.FullName
        }
    }

    throw "SignTool nao encontrado. Instale o Windows SDK com o componente Signing Tools for Desktop Apps."
}

function Invoke-CodeSigning {
    param([Parameter(Mandatory = $true)][string]$FilePath)

    if (-not $SigningEnabled) {
        if ($RequireSignature) {
            throw "Assinatura obrigatoria, mas nenhum certificado foi informado."
        }
        Write-Warning "Arquivo gerado sem assinatura digital: $FilePath"
        return
    }

    if (-not (Test-Path -LiteralPath $FilePath)) {
        throw "Arquivo para assinatura nao encontrado: $FilePath"
    }

    $SignTool = Find-SignTool
    $SignArguments = @(
        "sign",
        "/fd", "SHA256",
        "/tr", $TimestampUrl,
        "/td", "SHA256"
    )

    if (-not [string]::IsNullOrWhiteSpace($CertificateThumbprint)) {
        $NormalizedThumbprint = ($CertificateThumbprint -replace '\s', '').ToUpperInvariant()
        $SignArguments += @("/sha1", $NormalizedThumbprint)
    }
    else {
        if (-not (Test-Path -LiteralPath $CertificatePfxPath)) {
            throw "Certificado PFX nao encontrado: $CertificatePfxPath"
        }
        $SignArguments += @("/f", (Resolve-Path -LiteralPath $CertificatePfxPath).Path)
        if (-not [string]::IsNullOrWhiteSpace($env:PRONTU_SIGNING_PFX_PASSWORD)) {
            $SignArguments += @("/p", $env:PRONTU_SIGNING_PFX_PASSWORD)
        }
    }

    $SignArguments += (Resolve-Path -LiteralPath $FilePath).Path
    & $SignTool @SignArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao assinar digitalmente: $FilePath"
    }

    & $SignTool verify /pa /v (Resolve-Path -LiteralPath $FilePath).Path
    if ($LASTEXITCODE -ne 0) {
        throw "A assinatura foi aplicada, mas nao passou na verificacao: $FilePath"
    }
}

if (-not (Test-Path $EnvFile)) {
    throw "Arquivo .env nao encontrado na raiz do projeto."
}

$Allowed = @("SUPABASE_URL", "SUPABASE_KEY")
$Values = @{}
foreach ($Line in Get-Content $EnvFile) {
    if ($Line -match '^\s*([^#=]+?)\s*=\s*(.*)\s*$') {
        $Name = $Matches[1].Trim()
        $Value = $Matches[2].Trim().Trim('"').Trim("'")
        if ($Allowed -contains $Name) {
            $Values[$Name] = $Value
        }
    }
}

foreach ($Required in $Allowed) {
    if (-not $Values.ContainsKey($Required) -or [string]::IsNullOrWhiteSpace($Values[$Required])) {
        throw "Configuracao obrigatoria ausente no .env: $Required"
    }
}

New-Item -ItemType Directory -Force -Path $GeneratedDir | Out-Null
$PublicLines = @(
    "SUPABASE_URL=$($Values['SUPABASE_URL'])"
    "SUPABASE_KEY=$($Values['SUPABASE_KEY'])"
)
# Windows PowerShell 5 grava UTF-8 com uma marca invisivel (BOM). O arquivo
# publico precisa ser UTF-8 puro para a primeira variavel ser reconhecida.
[IO.File]::WriteAllLines(
    $PublicConfig,
    $PublicLines,
    [Text.UTF8Encoding]::new($false)
)

if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    $PythonCandidates = @(
        (Join-Path $Root ".venv\Scripts\python.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe")
    )
    $PythonExe = $PythonCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $PythonExe -or -not (Test-Path $PythonExe)) {
    throw "Python do Prontu nao encontrado. Informe -PythonExe com o caminho correto."
}

Push-Location $Root
try {
    & $PythonExe -m pytest -q
    if ($LASTEXITCODE -ne 0) {
        throw "Os testes automatizados falharam. O instalador nao sera gerado."
    }

    & $PythonExe -m PyInstaller --noconfirm --clean "installer\Prontu.spec"
    if ($LASTEXITCODE -ne 0) { throw "Falha ao gerar o aplicativo." }

    $ApplicationExe = Join-Path $Root "dist\Prontu\Prontu.exe"
    $Validation = Start-Process `
        -FilePath $ApplicationExe `
        -ArgumentList "--validate-installation" `
        -Wait `
        -PassThru `
        -WindowStyle Hidden
    if ($Validation.ExitCode -ne 0) {
        throw "O aplicativo empacotado falhou na validacao de recursos."
    }

    Invoke-CodeSigning -FilePath $ApplicationExe

    if ($SkipInstaller) {
        Write-Host "Aplicativo gerado em dist\Prontu" -ForegroundColor Green
        exit 0
    }

    $Candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    )
    $Iscc = $Candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $Iscc) {
        throw "Inno Setup 6 nao encontrado. Instale-o e execute este script novamente."
    }

    & $Iscc "/DMyAppVersion=$Version" "installer\Prontu.iss"
    if ($LASTEXITCODE -ne 0) { throw "Falha ao gerar o instalador." }

    $InstallerExe = Join-Path $Root "release\Prontu-Setup-$Version.exe"
    Invoke-CodeSigning -FilePath $InstallerExe
    Write-Host "Instalador pronto em $InstallerExe" -ForegroundColor Green
}
finally {
    Pop-Location
}
