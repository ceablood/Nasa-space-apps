@echo off
chcp 65001 >nul
title KOZMOGENIS
cd /d "%~dp0"
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo Python bulunamadi.
  echo https://www.python.org/downloads/ adresinden Python 3 kur.
  echo Kurarken "Add python.exe to PATH" kutusunu isaretle.
  pause
  exit /b 1
)
%PY% main.py
if errorlevel 1 pause
