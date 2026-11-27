param([switch]$Installer, [switch]$SkipInstall, [string]$Python = 'py')
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:OS -ne 'Windows_NT') { throw 'Execute este script no Windows x64.' }
$entrelaRoot = Split-Path $PSScriptRoot -Parent
Push-Location $entrelaRoot
try {
    $entrelaPython = Join-Path $entrelaRoot '.venv-release\Scripts\python.exe'
    if (-not (Test-Path $entrelaPython)) {
        if ([IO.Path]::GetFileNameWithoutExtension($Python) -eq 'py') {
            & $Python -3.12 -m venv .venv-release
        } else { & $Python -m venv .venv-release }
        if ($LASTEXITCODE -ne 0) { throw 'Não foi possível criar o ambiente Python 3.12.' }
    }
    function Invoke-EntrelaPython {
        & $entrelaPython @args
        if ($LASTEXITCODE -ne 0) { throw "Falha no Python: $args" }
    }
    Invoke-EntrelaPython -c "import sys,struct; assert sys.version_info[:2]==(3,12) and struct.calcsize('P')==8, 'Use Python 3.12 x64'"
    if (-not $SkipInstall) {
        Invoke-EntrelaPython -m pip install -r requirements-build.txt
        Invoke-EntrelaPython -m pip install --no-deps -e .
    }
    Invoke-EntrelaPython -m pip check
    $entrelaVersion = (& $entrelaPython -c 'from core import __version__; print(__version__)').Trim()
    if ($entrelaVersion -notmatch '^\d+\.\d+\.\d+$') { throw 'Versão inválida.' }
    Invoke-EntrelaPython -m PyInstaller --noconfirm --clean --distpath dist --workpath build\native packaging\Entrela.spec
    $entrelaRelease = Join-Path $entrelaRoot 'dist\release'
    New-Item -ItemType Directory -Force -Path $entrelaRelease | Out-Null
    $entrelaCheck = Join-Path $entrelaRoot 'build\native\verificacao.json'
    $entrelaExe = Join-Path $entrelaRoot 'dist\Entrela\Entrela.exe'
    $entrelaProcess = Start-Process -FilePath $entrelaExe -ArgumentList @('--verificar-pacote', "`"$entrelaCheck`"") -Wait -PassThru
    if ($entrelaProcess.ExitCode -ne 0) { throw "Falha ao verificar o executável. Consulte $entrelaCheck" }
    $entrelaReceipt = Get-Content $entrelaCheck -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $entrelaReceipt.success -or -not $entrelaReceipt.frozen) { throw 'A verificação não confirmou um executável independente.' }
    Copy-Item $entrelaCheck (Join-Path $entrelaRelease 'verificacao-portatil.json') -Force
    $entrelaZip = Join-Path $entrelaRelease "Entrela-$entrelaVersion-windows-x64-portatil.zip"
    Compress-Archive -Path dist\Entrela -DestinationPath $entrelaZip -Force
    if ($Installer) {
        $entrelaCompiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
        $entrelaIscc = if ($entrelaCompiler) { $entrelaCompiler.Source } else { Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe' }
        if (-not (Test-Path $entrelaIscc)) { throw 'Instale o Inno Setup 6 e execute novamente com -Installer. O ZIP portátil já foi gerado.' }
        & $entrelaIscc "/DAppVersion=$entrelaVersion" "/DBundleDir=$entrelaRoot\dist\Entrela" "/DReleaseDir=$entrelaRelease" packaging\Entrela.iss
        if ($LASTEXITCODE -ne 0) { throw 'Falha na criação do instalador.' }
    }
    Invoke-EntrelaPython -m pip freeze | Set-Content (Join-Path $entrelaRelease 'dependencias-build.txt') -Encoding UTF8
    $entrelaHashes = Get-ChildItem $entrelaRelease -File | Where-Object { $_.Extension -in '.zip', '.exe' } | Sort-Object Name | ForEach-Object {
        $entrelaHash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        "$entrelaHash  $($_.Name)"
    }
    $entrelaHashes | Set-Content (Join-Path $entrelaRelease 'SHA256SUMS.txt') -Encoding ASCII
    Write-Host "Arquivos prontos em $entrelaRelease"
} finally { Pop-Location }
