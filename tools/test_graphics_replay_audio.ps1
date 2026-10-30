param([Parameter(Mandatory=$true)][string]$Root)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $Root){throw 'Use a new synthetic test directory'}
New-Item -ItemType Directory -Path $Root|Out-Null
$taskAudioRoot=(Resolve-Path -LiteralPath $Root).Path
$taskProtected=Join-Path $taskAudioRoot 'normal-game.ini'
[IO.File]::WriteAllText($taskProtected,"[Audio]`nSound Volume=0`nMusic Volume=0`n")
$taskProtectedHash=(Get-FileHash -LiteralPath $taskProtected).Hash
foreach($taskCase in @('existing','missing')){
 $taskDir=Join-Path $taskAudioRoot $taskCase;New-Item -ItemType Directory -Path $taskDir|Out-Null
 $taskConfig=Join-Path $taskDir 'diablo.ini'
 $taskText=if($taskCase -eq 'existing'){"[audio]`nsound volume=0`nMusic Volume = 0`nSample Rate=48000`n[Graphics]`nWidth=768`n"}else{"[Graphics]`nWidth=768`n"}
 [IO.File]::WriteAllText($taskConfig,$taskText)
 & (Join-Path $PSScriptRoot 'run_gpu_replay.ps1') -Root $taskAudioRoot -Case $taskCase -ConfigureOnly
 $taskResult=[IO.File]::ReadAllText($taskConfig)
 foreach($taskKey in @('Sound Volume','Music Volume','Audio Cues Volume')){
  $taskPattern='(?im)^[ \t]*'+[regex]::Escape($taskKey)+'[ \t]*=[ \t]*-1600[ \t]*$'
  if([regex]::Matches($taskResult,$taskPattern).Count -ne 1){throw ('Missing or duplicate mute setting: '+$taskKey)}
 }
 if($taskResult -notmatch 'Width=768'){throw 'Unrelated test options changed'}
 if($taskCase -eq 'existing' -and $taskResult -notmatch 'Sample Rate=48000'){throw 'Unrelated audio options changed'}
 $taskProof=Get-Content -LiteralPath (Join-Path $taskAudioRoot ($taskCase+'-audio.json')) -Raw|ConvertFrom-Json
 if($taskProof.mode -ne 'muted'){throw 'Missing mute proof'}
}
if((Get-FileHash -LiteralPath $taskProtected).Hash -ne $taskProtectedHash){throw 'Normal-game settings changed'}
Write-Output 'PASS: graphics replay music/effects/cues muted; existing options and normal-game settings preserved; no game launched'
