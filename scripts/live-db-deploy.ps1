<#
.SYNOPSIS
  Owner-only Deploy steps 1-2: back up the live database, then apply migration file(s) to it.

.DESCRIPTION
  Run this yourself; agents never run it (R-0009). It asks for the live database address
  (the session pooler URL) without echoing it, and never writes it to disk.

  1. Takes two backups into C:\backups (schema and data) and stops if either is empty.
  2. Applies each named file from supabase/migrations, in the order given, stopping at the
     first error.

  Needs Docker running. Run it BEFORE merging or updating the live folder.

.EXAMPLE
  .\scripts\live-db-deploy.ps1 20261101000000_word_count.sql
#>
param(
    [Parameter(Mandatory = $true, Position = 0, ValueFromRemainingArguments = $true)]
    [string[]] $Migrations,
    [string] $BackupDir = "C:\backups",
    # Only for testing the script against the local dev database.
    [string] $DbUrl
)

# Not "Stop": Windows PowerShell treats a tool's progress messages on stderr as errors.
# Each step checks its exit code instead.
$repo = Split-Path -Parent $PSScriptRoot
$supabase = "supabase@2.122.0"
$psqlImage = "public.ecr.aws/supabase/postgres:17.11.0.006"

function Fail($message) {
    Write-Host "STOPPED: $message" -ForegroundColor Red
    exit 1
}

# Check every migration file exists before touching anything.
$files = foreach ($name in $Migrations) {
    $path = Join-Path $repo "supabase\migrations\$name"
    if (-not (Test-Path $path)) { Fail "no such migration: supabase\migrations\$name" }
    Get-Item $path
}

docker info --format "{{.ServerVersion}}" *> $null
if ($LASTEXITCODE -ne 0) { Fail "Docker isn't running. Start Docker Desktop and try again." }

if (-not $DbUrl) {
    $secure = Read-Host "Live database address (session pooler URL; not shown)" -AsSecureString
    $DbUrl = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
}
if ($DbUrl -notmatch '^postgres(ql)?(\+psycopg)?://') { Fail "that doesn't look like a database address." }
# The worker's form (postgresql+psycopg://) isn't understood by the database tools.
$DbUrl = $DbUrl -replace '^postgresql\+psycopg://', 'postgresql://'

# 1. Backup
New-Item -ItemType Directory -Force -Path $BackupDir -ErrorAction Stop | Out-Null
$stamp = Get-Date -Format "yyyy-MM-dd-HHmm"
$schemaFile = Join-Path $BackupDir "readurlist-$stamp-schema.sql"
$dataFile = Join-Path $BackupDir "readurlist-$stamp-data.sql"

Write-Host "Backing up the schema..."
npx -y $supabase db dump --db-url $DbUrl -f $schemaFile
if ($LASTEXITCODE -ne 0) { Fail "schema backup failed; nothing was changed." }
Write-Host "Backing up the data..."
npx -y $supabase db dump --db-url $DbUrl --data-only -f $dataFile
if ($LASTEXITCODE -ne 0) { Fail "data backup failed; nothing was changed." }

foreach ($f in @($schemaFile, $dataFile)) {
    if (-not (Test-Path $f) -or (Get-Item $f).Length -eq 0) { Fail "backup $f is empty; nothing was changed." }
}
Write-Host ("Backup done: {0} ({1:N0} KB), {2} ({3:N0} KB)" -f `
    $schemaFile, ((Get-Item $schemaFile).Length / 1KB), $dataFile, ((Get-Item $dataFile).Length / 1KB))

# 2. Migrations
foreach ($file in $files) {
    Write-Host "Applying $($file.Name)..."
    Get-Content -Raw $file.FullName |
        docker run --rm -i --entrypoint psql $psqlImage $DbUrl -v ON_ERROR_STOP=1 -q -f -
    if ($LASTEXITCODE -ne 0) { Fail "$($file.Name) failed. The backup is in $BackupDir." }
    Write-Host "Applied $($file.Name)." -ForegroundColor Green
}

Write-Host "Done. Next: merge the pull request, then update the live folder." -ForegroundColor Green
