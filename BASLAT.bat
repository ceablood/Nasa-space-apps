@echo off
chcp 65001 >nul
title AETHER-X
cd /d "%~dp0"
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo Python was not found.
  echo Install Python 3 from https://www.python.org/downloads/
  echo While installing, tick the "Add python.exe to PATH" box.
  pause
  exit /b 1
)
%PY% main.py
if errorlevel 1 pause
