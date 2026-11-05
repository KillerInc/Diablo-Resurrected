param([Parameter(Mandatory=$true)][string]$Root,[string]$Case='frontend',[Parameter(Mandatory=$true)][string]$Executable,[string]$DataDirectory='D:/Games/Diablo',[ValidateRange(1,60)][int]$DurationSeconds=15,[switch]$ShowTitle)
$ErrorActionPreference='Stop'
if($Case -notmatch '^[a-zA-Z0-9_-]+$'){throw 'Use a simple isolated case name'}
$taskRoot=(Resolve-Path -LiteralPath $Root).Path
$taskSave=Join-Path $taskRoot $Case
& (Join-Path $PSScriptRoot 'run_gpu_replay.ps1') -Root $taskRoot -Case $Case -ConfigureOnly
if($ShowTitle){
    $taskIni=Join-Path $taskSave 'diablo.ini'
    $taskText=[IO.File]::ReadAllText($taskIni)
    $taskText=[regex]::Replace($taskText,'(?m)^Splash=[^\r\n]*','Splash=1')
    $taskText=[regex]::Replace($taskText,'(?m)^Diablo Intro=[^\r\n]*','Diablo Intro=0')
    [IO.File]::WriteAllText($taskIni,$taskText,[Text.UTF8Encoding]::new($false))
}
$taskExe=(Resolve-Path -LiteralPath $Executable).Path
$env:D1R_TEST_AUDIO_GAIN='0.5';$env:D1R_TEST_DISPLAY='left'
$env:D1R_FRAME_DUMP=Join-Path $taskRoot ($Case+'-captures');$env:D1R_FRAME_DUMP_UI='1';$env:D1R_PROFILE_HD='1'
New-Item -ItemType Directory -Force $env:D1R_FRAME_DUMP|Out-Null
$taskSkip=if($ShowTitle){''}else{' -n'}
$taskArgs='--diablo --save-dir "'+$taskSave+'" --config-dir "'+$taskSave+'" --data-dir "'+$DataDirectory+'" --verbose --log-to-file "'+(Join-Path $taskRoot ($Case+'.log'))+'"'+$taskSkip
$taskProcess=$null;$taskStopped=$false
try{
    $taskProcess=Start-Process -FilePath $taskExe -ArgumentList $taskArgs -WorkingDirectory (Split-Path $taskExe) -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskRoot ($Case+'-stdout.log')) -RedirectStandardError (Join-Path $taskRoot ($Case+'-stderr.log'))
    for($taskSecond=0;$taskSecond -lt $DurationSeconds;$taskSecond++){if($taskProcess.WaitForExit(1000)){break}}
    if(-not $taskProcess.HasExited){$taskProcess.Kill();$taskStopped=$true}
    $taskProcess.WaitForExit()
    $taskCount=@(Get-ChildItem -LiteralPath $env:D1R_FRAME_DUMP -Filter '*.png').Count
    @{executable_sha256=(Get-FileHash -LiteralPath $taskExe).Hash;intentional_stop=$taskStopped;captures=$taskCount;muted=$true;display='left';title=[bool]$ShowTitle}|ConvertTo-Json|Set-Content (Join-Path $taskRoot ($Case+'-process.json'))
    if($taskCount -eq 0){throw 'No frontend GPU captures were produced'}
    if(-not $taskStopped -and $taskProcess.ExitCode -ne 0){throw 'Frontend exited unexpectedly'}
    Write-Output ($Case+': '+$taskCount+' private captures; muted on left display')
}finally{
    if($taskProcess -and -not $taskProcess.HasExited){$taskProcess.Kill()}
    Remove-Item Env:D1R_FRAME_DUMP_UI -ErrorAction SilentlyContinue
    Remove-Item Env:D1R_PROFILE_HD -ErrorAction SilentlyContinue
}
