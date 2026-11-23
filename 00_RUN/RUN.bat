@echo off
cd /d "%~dp0"
start "GDELT IPI task" /min py -3 dispatch.py
