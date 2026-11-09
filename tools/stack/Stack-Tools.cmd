@echo off
rem Double-click launcher for the stack tools in this folder.
cd /d "%~dp0"
where pwsh >nul 2>nul
if errorlevel 1 goto nopwsh
set "PS=pwsh -NoProfile -ExecutionPolicy Bypass -File"
rem Repo: STACK_REPO if set, else the clone this folder is in (resolved by the .ps1 scripts).
set "REPO=%STACK_REPO%"
if not defined REPO set "REPO=clone containing %~dp0"

:menu
cls
echo.
echo   STACK TOOLS   (repo: %REPO%)
echo   ------------------------------------------------------------
echo   1  List stacks with conflicts           (changes nothing)
echo   2  Fix ALL conflicting stacks           (report, asks before push)
echo   3  Fix ALL + run tests                  (slower, safer)
echo   4  Pick a repo / one stack from a menu
echo   5  Fix one stack by PR number
echo   Q  Quit
echo.
set "c="
set /p "c=  Choose 1-5 or Q: "
if /i "%c%"=="q" exit /b 0
if "%c%"=="1" goto list
if "%c%"=="2" goto fixall
if "%c%"=="3" goto fixtest
if "%c%"=="4" goto pick
if "%c%"=="5" goto bypr
goto menu

:list
%PS% "%~dp0Fix-AllStacks.ps1" -ListOnly
goto done

:fixall
%PS% "%~dp0Fix-AllStacks.ps1"
goto done

:fixtest
%PS% "%~dp0Fix-AllStacks.ps1" -Test "python -m pytest -q -p no:cacheprovider tests"
goto done

:pick
%PS% "%~dp0Stack-Helper.ps1"
goto done

:bypr
set "pr="
set /p "pr=  PR number (e.g. 2145): "
if not defined pr goto menu
%PS% "%~dp0Rebase-Stack.ps1" %pr%
set "push="
set /p "push=  Looks right? Push it now? [y/N]: "
if /i "%push%"=="y" %PS% "%~dp0Rebase-Stack.ps1" %pr% -Push
goto done

:done
echo.
pause
goto menu

:nopwsh
echo PowerShell 7 (pwsh) was not found. Install it with:  winget install Microsoft.PowerShell
pause
exit /b 1
