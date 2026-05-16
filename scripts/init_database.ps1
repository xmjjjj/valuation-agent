# Initialize MySQL schema + seed (no Docker required).
# Usage (PowerShell):
#   .\scripts\init_database.ps1
#   .\scripts\init_database.ps1 -MysqlExe "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"

param(
    [string]$MysqlExe = "",
    [string]$Host = "127.0.0.1",
    [int]$Port = 3306,
    [string]$User = "root",
    [string]$Password = "",
    [string]$Database = "patent_valuation"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$InitDir = Join-Path $ProjectRoot "db\init"

function Find-MysqlExe {
    if ($MysqlExe -and (Test-Path $MysqlExe)) { return $MysqlExe }
    $cmd = Get-Command mysql -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = @(
        "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe",
        "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe",
        "C:\Program Files\MySQL\MySQL Server 5.7\bin\mysql.exe",
        "C:\xampp\mysql\bin\mysql.exe",
        "C:\phpstudy_pro\Extensions\MySQL*\bin\mysql.exe"
    )
    foreach ($path in $candidates) {
        $resolved = Resolve-Path $path -ErrorAction SilentlyContinue
        if ($resolved) { return $resolved[0].Path }
    }
    return $null
}

if (-not $Password) {
    $secure = Read-Host "MySQL password for user '$User'" -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    $Password = [Runtime.InteropServices.Marshal]::PtrToStringAuto($ptr)
}

$mysql = Find-MysqlExe
if (-not $mysql) {
    Write-Host "mysql.exe not found. Install MySQL Server or pass -MysqlExe path." -ForegroundColor Red
    exit 1
}

Write-Host "Using: $mysql"

$env:MYSQL_PWD = $Password
$baseArgs = @("-h", $Host, "-P", "$Port", "-u", $User, "--default-character-set=utf8mb4")

& $mysql @baseArgs -e "CREATE DATABASE IF NOT EXISTS ``$Database`` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $mysql @baseArgs -e "CREATE USER IF NOT EXISTS 'patent'@'%' IDENTIFIED BY 'patent_dev';"
& $mysql @baseArgs -e "CREATE USER IF NOT EXISTS 'patent'@'localhost' IDENTIFIED BY 'patent_dev';"
& $mysql @baseArgs -e "GRANT ALL PRIVILEGES ON ``$Database``.* TO 'patent'@'%';"
& $mysql @baseArgs -e "GRANT ALL PRIVILEGES ON ``$Database``.* TO 'patent'@'localhost';"
& $mysql @baseArgs -e "FLUSH PRIVILEGES;"

foreach ($file in @("01_schema.sql", "02_seed.sql")) {
    $path = Join-Path $InitDir $file
    Write-Host "Running $file ..."
    Get-Content $path -Raw -Encoding UTF8 | & $mysql @baseArgs $Database
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Remove-Item Env:MYSQL_PWD -ErrorAction SilentlyContinue
Write-Host "Done. Database '$Database' is ready." -ForegroundColor Green
