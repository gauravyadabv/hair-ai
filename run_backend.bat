@echo off
title Hair Health AI - Backend Server
echo ========================================================
echo Starting Hair Health AI Backend API on 127.0.0.1:8000
echo ========================================================
cd /d "%~dp0"
set PYTHONPATH=backend
backend\venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload
pause

