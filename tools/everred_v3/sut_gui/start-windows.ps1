param(
    [Parameter(Mandatory=$true)][string]$SutRoot,
    [int]$Port = 8765,
    [switch]$EnableExecution
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path (Join-Path $SutRoot 'src/everred.py'))) {
    throw "EVERRED SUT not found: $SutRoot\src\everred.py"
}
$server = Join-Path $PSScriptRoot 'server.py'
$python = Get-Command py -ErrorAction SilentlyContinue
if ($python) { $command = @('-3', $server, '--sut-root', $SutRoot, '--port', "$Port") ; $exe = 'py' }
else { $command = @($server, '--sut-root', $SutRoot, '--port', "$Port") ; $exe = 'python' }
if ($EnableExecution) { $command += '--enable-execution' }
Write-Host "CODE PURPLE -> http://127.0.0.1:$Port/"
Write-Host 'For execution, enter the token printed by the Python server into the local page.'
& $exe @command
