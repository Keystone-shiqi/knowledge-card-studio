@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
set "WORKFLOW_PYTHON="
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -c "import sys; assert sys.version_info >= (3,9)" >nul 2>nul
  if not errorlevel 1 set "WORKFLOW_PYTHON=py -3"
)
if not defined WORKFLOW_PYTHON (
  python -c "import sys; assert sys.version_info >= (3,9)" >nul 2>nul
  if not errorlevel 1 set "WORKFLOW_PYTHON=python"
)
if not defined WORKFLOW_PYTHON (
  echo 请先安装 Python 3.11 或更新版本，并重启 WorkBuddy。
  echo https://www.python.org/downloads/windows/
  pause
  exit /b 2
)
%WORKFLOW_PYTHON% -X utf8 scripts\portable.py menu
pause
