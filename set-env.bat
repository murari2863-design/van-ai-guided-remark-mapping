@echo off
setlocal enabledelayedexpansion

if "%~1"=="" (
    echo Usage: set-env.bat OIDC_REDIRECT_URI
    echo Example: set-env.bat https://van-ai-guided-data-entry.apps.your-domain.com
    exit /b 1
)

set OIDC_REDIRECT_URI=%~1

if not exist "server\.env" (
    echo Error: server\.env file not found!
    exit /b 1
)

echo Setting environment variables for van-ai-guided-data-entry...

REM Read and set environment variables from server\.env
REM Start at LLM_API_KEY; ignore commented lines and inline comments after values
set "processing=0"
for /f "usebackq tokens=1,* delims==" %%a in ("server\.env") do (
    set "rawKey=%%~a"
    set "rawVal=%%~b"

    call :trim key "!rawKey!"
    call :trim value "!rawVal!"

    REM Skip empty or commented lines (handles leading spaces before #)
    if defined key if not "!key:~0,1!"=="#" (
        REM Strip inline comments from value (everything after '#')
        for /f "tokens=1 delims=#" %%c in ("!value!") do set "value=%%~c"
        call :trim value "!value!"

        REM Start processing once we hit OIDC_ISSUER
        if "!processing!"=="0" (
            if /i "!key!"=="OIDC_ISSUER" set "processing=1"
        )

        if "!processing!"=="1" (
            echo Setting !key!...
            cf set-env van-ai-guided-data-entry !key! "!value!"
        )
    )
)

REM Override OIDC_REDIRECT_URI with the provided argument
echo Setting OIDC_REDIRECT_URI...
cf set-env van-ai-guided-data-entry OIDC_REDIRECT_URI "%OIDC_REDIRECT_URI%"


REM Update client base URL in settings.ts based on OIDC_REDIRECT_URI and rebuild
echo Updating client base URL from OIDC_REDIRECT_URI and rebuilding client...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $uri=[Uri]$env:OIDC_REDIRECT_URI; $base=($uri.Scheme + '://' + $uri.Authority); Write-Host ('Computed BASE URL: ' + $base); $file='client\src\data\settings.ts'; if(-not (Test-Path $file)){ throw 'File not found: ' + $file } $content=[IO.File]::ReadAllText($file); $pattern='const PROD_API_BASE_URL\s*=\s*\".*?\";'; $replacement=('const PROD_API_BASE_URL = \"' + $base + '\";'); $newContent=[Text.RegularExpressions.Regex]::Replace($content,$pattern,$replacement); [IO.File]::WriteAllText($file,$newContent)"

if errorlevel 1 (
    echo Error: Failed to update client settings.ts with base URL.
    exit /b 1
)

pushd client
call pnpm install
if errorlevel 1 (
    echo Error: pnpm install failed.
    popd
    exit /b 1
)
call pnpm build
set buildExitCode=%ERRORLEVEL%
popd
if not "%buildExitCode%"=="0" (
    echo Error: Frontend build failed!
    exit /b %buildExitCode%
)

echo Environment variables set successfully and client rebuilt!
goto :eof

:trim
REM %1 = var name to set, %2 = value to trim (leading/trailing spaces)
setlocal enabledelayedexpansion
set "s=%~2"
for /f "tokens=* delims= " %%t in ("!s!") do set "s=%%t"
:trim_end
if "!s:~-1!"==" " set "s=!s:~0,-1!" & goto trim_end
endlocal & set "%~1=%s%"
exit /b
