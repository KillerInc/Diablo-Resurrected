param([Parameter(Mandatory=$true)][string]$Root,[Parameter(Mandatory=$true)][string]$Fixture,[Parameter(Mandatory=$true)][string]$Executable,[Parameter(Mandatory=$true)][string]$Python,[int]$Ticks=12000)
$ErrorActionPreference='Stop'
$taskRoot=(Resolve-Path -LiteralPath $Root).Path
$taskFixture=(Resolve-Path -LiteralPath $Fixture).Path
$taskExe=(Resolve-Path -LiteralPath $Executable).Path
function Run-Case([string]$Name,[bool]$Cache,[bool]$Profile){
    & $Python "$PSScriptRoot/ui_benchmark.py" prepare $taskFixture (Join-Path $taskRoot $Name) --ticks $Ticks
    if($LASTEXITCODE){throw 'Cannot prepare fixed replay'}
    $env:D1R_GPU_INVENTORY_CACHE=if($Cache){'1'}else{'0'}
    if($Profile){
        $env:D1R_CPU_PROFILE_LOG=Join-Path $taskRoot ($Name+'-stages.csv')
        $env:D1R_GPU_PROFILE_LOG=Join-Path $taskRoot ($Name+'-gpu.csv')
        $env:D1R_PROFILE_HD='1'
    }
    & "$PSScriptRoot/run_gpu_replay.ps1" -Root $taskRoot -Case $Name -Executable $taskExe -Demo 7 -TimeoutSeconds 300
    Remove-Item Env:D1R_CPU_PROFILE_LOG,Env:D1R_GPU_PROFILE_LOG,Env:D1R_PROFILE_HD -ErrorAction SilentlyContinue
}
try{
    # Normal FPS runs have no capture, hardware queries or thread-clock reads.
    Run-Case off-a $false $false
    Run-Case on-a $true $false
    Run-Case on-b $true $false
    Run-Case off-b $false $false
    Run-Case profile-off $false $true
    Run-Case profile-on $true $true
    & $Python "$PSScriptRoot/ui_benchmark.py" analyze $taskRoot off-a on-a on-b off-b profile-off profile-on > (Join-Path $taskRoot 'steady-results.json')
    if($LASTEXITCODE){throw 'Steady-window validation failed'}
}finally{
    Remove-Item Env:D1R_GPU_INVENTORY_CACHE,Env:D1R_CPU_PROFILE_LOG,Env:D1R_GPU_PROFILE_LOG,Env:D1R_PROFILE_HD -ErrorAction SilentlyContinue
}
