param(
    [Parameter(Mandatory=$true)][string]$SutRoot,
    [int]$Port = 8765,
    [switch]$EnableExecution,
    [switch]$EnableOperator,
    [string]$AbacusRoot,
    [string]$InboxDir,
    [string]$ReceiptDir
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
if ($AbacusRoot) { $command += @('--abacus-root', $AbacusRoot) }
if ($InboxDir) { $command += @('--operator-inbox', $InboxDir) }
if ($ReceiptDir) { $command += @('--operator-receipts', $ReceiptDir) }
if ($EnableOperator) {
    if (-not $AbacusRoot) { throw '-EnableOperator requires -AbacusRoot' }
    $command += '--enable-operator'
}
Write-Host "CODE PURPLE -> http://127.0.0.1:$Port/"
if ($AbacusRoot) { Write-Host "Operator -> http://127.0.0.1:$Port/operator" }
Write-Host 'For execution, enter the token printed by the Python server into the local page.'
& $exe @command
