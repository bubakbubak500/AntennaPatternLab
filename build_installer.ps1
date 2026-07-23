param(
    [string]$Compiler = "",
    [string]$SignTool = "",
    [string]$CertificateThumbprint = "",
    [string]$ReleaseBaseUrl = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptPath = Join-Path $projectRoot "installer\AntennaPatternLab.iss"
$projectMetadata = Get-Content -LiteralPath (Join-Path $projectRoot "pyproject.toml") -Raw
$version = [regex]::Match($projectMetadata, '(?m)^version\s*=\s*"([^"]+)"').Groups[1].Value
if ($version -notmatch '^\d+\.\d+\.\d+$') {
    throw "Project version must use major.minor.patch format."
}
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot "dist\AntennaPatternLab\AntennaPatternLab.exe"))) {
    throw "Nejprve vytvořte PyInstaller build pomocí build_exe.bat."
}
if (-not $Compiler) {
    $candidates = @(
        (Join-Path $projectRoot "tools\Inno Setup 6\ISCC.exe"),
        (Join-Path $projectRoot "tools\InnoSetup6\ISCC.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
    )
    $Compiler = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $Compiler -or -not (Test-Path -LiteralPath $Compiler)) {
    throw "ISCC.exe nebyl nalezen. Nainstalujte Inno Setup z https://jrsoftware.org/isdl.php."
}
if ($SignTool) {
    if (-not (Test-Path -LiteralPath $SignTool)) { throw "SignTool nebyl nalezen." }
    if ($CertificateThumbprint -notmatch '^[0-9A-Fa-f]{40}$') {
        throw "Pro podpis zadejte 40znakový SHA-1 thumbprint code-signing certifikátu."
    }
    $signCommand = '$q' + $SignTool + '$q sign /fd SHA256 /sha1 ' + $CertificateThumbprint + ' /td SHA256 /tr http://timestamp.digicert.com $f'
    & $Compiler "/DMyAppVersion=$version" "/Saplsign=$signCommand" "/DEnableSigning=1" $scriptPath
} else {
    & $Compiler "/DMyAppVersion=$version" $scriptPath
}
if ($LASTEXITCODE -ne 0) { throw "Sestavení instalátoru selhalo." }

$installer = Join-Path $projectRoot "release\AntennaPatternLab-$version-setup-win-x64.exe"
$hash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLowerInvariant()
if ($ReleaseBaseUrl) {
    if ($ReleaseBaseUrl -notmatch '^https://') { throw "ReleaseBaseUrl musí používat HTTPS." }
    $base = $ReleaseBaseUrl.TrimEnd('/')
    $manifest = [ordered]@{
        version = $version
        installer_url = "$base/AntennaPatternLab-$version-setup-win-x64.exe"
        sha256 = $hash
        notes_url = "https://github.com/bubakbubak500/AntennaPatternLab/releases/tag/v$version"
    }
    $manifest | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $projectRoot "release\release-manifest.json") -Encoding UTF8
}
Get-FileHash -LiteralPath $installer -Algorithm SHA256
