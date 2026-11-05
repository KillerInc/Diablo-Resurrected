param([Parameter(Mandatory=$true)][string]$Root,[Parameter(Mandatory=$true)][string]$Case,[Parameter(Mandatory=$true)][string]$Executable,[int]$Demo=7,[switch]$Profile,[switch]$Capture,[string]$DataDirectory='D:\Games\Diablo')
$ErrorActionPreference='Stop'
$taskRoot=(Resolve-Path -LiteralPath $Root).Path
$taskSave=(Resolve-Path -LiteralPath (Join-Path $taskRoot $Case)).Path
$taskExecutable=(Resolve-Path -LiteralPath $Executable).Path
# Root/Case must contain an isolated full-game save and a prepared replay.
& (Join-Path $PSScriptRoot 'run_gpu_replay.ps1') -Root $taskRoot -Case $Case -ConfigureOnly
$env:D1R_TEST_AUDIO_GAIN='0.5'
$env:D1R_TEST_DISPLAY='left'
$env:D1R_PERF_LOG=Join-Path $taskRoot ($Case+'-performance.csv')
Remove-Item -LiteralPath $env:D1R_PERF_LOG -ErrorAction SilentlyContinue
if($Profile){$env:D1R_PROFILE_HD='1'}else{Remove-Item Env:D1R_PROFILE_HD -ErrorAction SilentlyContinue}
if($Capture){$env:D1R_FRAME_DUMP=Join-Path $taskRoot ($Case+'-captures');New-Item -ItemType Directory -Force $env:D1R_FRAME_DUMP|Out-Null}else{Remove-Item Env:D1R_FRAME_DUMP -ErrorAction SilentlyContinue}
$taskLog=Join-Path $taskRoot ($Case+'.log')
$taskArgs='--diablo --demo '+$Demo+' --timedemo --save-dir "'+$taskSave+'" --config-dir "'+$taskSave+'" --data-dir "'+$DataDirectory+'" --verbose --log-to-file "'+$taskLog+'" -n'
$taskHash=(Get-FileHash -LiteralPath $taskExecutable -Algorithm SHA256).Hash
$taskClock=[Diagnostics.Stopwatch]::StartNew()
$taskProcess=Start-Process -FilePath $taskExecutable -ArgumentList $taskArgs -WorkingDirectory $DataDirectory -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskRoot ($Case+'-stdout.log')) -RedirectStandardError (Join-Path $taskRoot ($Case+'-stderr.log'))
while(-not $taskProcess.WaitForExit(1000)){if($taskClock.Elapsed.TotalSeconds -gt 900){$taskProcess.Kill();throw 'Sprite performance probe timed out'}}
$taskProcess.WaitForExit()
@{executable_sha256=$taskHash;exit=$taskProcess.ExitCode;elapsed_seconds=$taskClock.Elapsed.TotalSeconds;profile=[bool]$Profile;capture=[bool]$Capture}|ConvertTo-Json|Set-Content (Join-Path $taskRoot ($Case+'-process.json'))
if($taskProcess.ExitCode -ne 0){throw ('Sprite performance probe failed: '+$taskProcess.ExitCode)}
Get-Content -LiteralPath $taskLog -Tail 3
