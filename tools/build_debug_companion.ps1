param([string]$DependencyBuild,[string]$BuildDirectory,[string]$CMake,[switch]$ConfigureOnly)
$ErrorActionPreference='Stop'
$taskRepo=Split-Path -Parent $PSScriptRoot
if(-not $DependencyBuild){$DependencyBuild=Join-Path $taskRepo 'build-win64-sdl3'}
if(-not $BuildDirectory){$BuildDirectory=Join-Path $taskRepo 'build-win64-sdl3-debug-companion'}
if(-not $CMake){$CMake='C:/Program Files/Microsoft Visual Studio/2022/Community/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe'}
$taskCache=Join-Path $DependencyBuild 'CMakeCache.txt'
if(-not(Test-Path -LiteralPath $taskCache)){throw 'The validated SDL3 dependency build is required'}
$taskValues=@{}
foreach($taskLine in [IO.File]::ReadAllLines($taskCache)){if($taskLine -match '^([^/#][^:]*):[^=]+=(.*)$'){$taskValues[$matches[1]]=$matches[2]}}
$taskArgs=@('-S',$taskRepo,'-B',$BuildDirectory,'-G','Visual Studio 17 2022','-A','x64','-DCMAKE_CONFIGURATION_TYPES=Debug','-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDebug','-DDEBUG=ON','-DREINCARNATED_DEBUG_COMPANION=ON','-DUSE_SDL3=ON','-DBUILD_TESTING=OFF','-DCPACK=OFF','-DDISABLE_LTO=ON','-DDISABLE_ZERO_TIER=ON','-DDISABLE_DEMOMODE=OFF','-DVCPKG_MANIFEST_INSTALL=OFF','-DFETCHCONTENT_FULLY_DISCONNECTED=ON',('-DCMAKE_TOOLCHAIN_FILE='+$taskValues['CMAKE_TOOLCHAIN_FILE']),('-DVCPKG_TARGET_TRIPLET='+$taskValues['VCPKG_TARGET_TRIPLET']),('-DVCPKG_INSTALLED_DIR='+(Join-Path $DependencyBuild 'vcpkg_installed')))
foreach($taskKey in $taskValues.Keys){if($taskKey -notmatch '-STRINGS$' -and $taskKey -match '^DEVILUTIONX_(SYSTEM_|STATIC_|DISPLAY_TEXTURE_FORMAT$|RESAMPLER_SDL$|DISABLE_EXCEPTIONS$)'){$taskArgs+=('-D'+$taskKey+'='+$taskValues[$taskKey])}}
foreach($taskSource in Get-ChildItem -LiteralPath (Join-Path $DependencyBuild '_deps') -Directory -Filter '*-src'){$taskContentName=$taskSource.Name.Substring(0,$taskSource.Name.Length-4).ToUpperInvariant();$taskArgs+=('-DFETCHCONTENT_SOURCE_DIR_'+$taskContentName+'='+$taskSource.FullName)}
& $CMake @taskArgs
if($LASTEXITCODE -ne 0){throw 'Debug companion configuration failed'}
if(-not $ConfigureOnly){& $CMake --build $BuildDirectory --config Debug --target devilutionx --parallel 4;if($LASTEXITCODE -ne 0){throw 'Debug companion build failed'}}
