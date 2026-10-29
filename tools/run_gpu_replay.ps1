param([Parameter(Mandatory=$true)][string]$Root,[string]$Case='ui',[int]$Demo=1,[switch]$Capture,[switch]$NormalSpeed,[switch]$DisableGpuSprites,[string]$Executable)
$ErrorActionPreference='Stop'
$taskRoot=(Resolve-Path -LiteralPath $Root).Path
$taskPackage=Join-Path $taskRoot 'package';$taskSave=Join-Path $taskRoot $Case
$taskExecutable=Join-Path $taskPackage 'Diablo Reincarnated.exe'
if($Executable){$taskExecutable=(Resolve-Path -LiteralPath $Executable).Path;$taskPackage=Split-Path -Parent $taskExecutable}
$env:D1R_TEST_AUDIO_GAIN='0.5';$env:D1R_TRACE_PLAYER_SHEETS='1'
$env:D1R_PERF_LOG=Join-Path $taskRoot ($Case+'-performance.csv');$env:D1R_SHEET_LOG=Join-Path $taskRoot ($Case+'-sheets.log')
if($DisableGpuSprites){$env:D1R_DISABLE_GPU_SPRITES='1'}else{Remove-Item Env:D1R_DISABLE_GPU_SPRITES -ErrorAction SilentlyContinue}
if($Capture){$env:D1R_FRAME_DUMP=Join-Path $taskRoot ($Case+'-captures');New-Item -ItemType Directory -Force $env:D1R_FRAME_DUMP|Out-Null}else{Remove-Item Env:D1R_FRAME_DUMP -ErrorAction SilentlyContinue}
$taskTimed=if($NormalSpeed){''}else{' --timedemo'}
$taskArgs='--spawn --diablo --demo '+$Demo+$taskTimed+' --save-dir "'+$taskSave+'" --config-dir "'+$taskSave+'" --data-dir "D:\Games\Diablo" --verbose --log-to-file "'+(Join-Path $taskRoot ($Case+'.log'))+'" -n'
$taskClock=[Diagnostics.Stopwatch]::StartNew()
$taskProcess=Start-Process -FilePath $taskExecutable -ArgumentList $taskArgs -WorkingDirectory $taskPackage -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskRoot ($Case+'-stdout.log')) -RedirectStandardError (Join-Path $taskRoot ($Case+'-stderr.log'))
$taskPeak=0L;$taskWorkingSet=0L
while(-not $taskProcess.WaitForExit(1000)){$taskProcess.Refresh();$taskPeak=[Math]::Max($taskPeak,$taskProcess.PrivateMemorySize64);$taskWorkingSet=[Math]::Max($taskWorkingSet,$taskProcess.WorkingSet64);if($taskClock.Elapsed.TotalSeconds -gt 360){$taskProcess.Kill();throw 'Isolated GPU replay timeout'}}
$taskProcess.WaitForExit()
@{exit=$taskProcess.ExitCode;peak_private_bytes=$taskPeak;peak_working_set_bytes=$taskWorkingSet;elapsed_seconds=$taskClock.Elapsed.TotalSeconds}|ConvertTo-Json|Set-Content (Join-Path $taskRoot ($Case+'-process.json'))
Write-Output ($Case+': exit '+$taskProcess.ExitCode+' after '+[int]$taskClock.Elapsed.TotalSeconds+' seconds')
if($taskProcess.ExitCode -ne 0){throw 'GPU replay failed'}
