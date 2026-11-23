@echo off
cd /d "%~dp0.."
echo Installing Claude Code... > logs\install_claude_code.txt
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://claude.ai/install.ps1 | iex" >> logs\install_claude_code.txt 2>&1
powershell -NoProfile -Command "$p=[Environment]::GetEnvironmentVariable('Path','User'); $b=Join-Path $env:USERPROFILE '.local\bin'; if ($p -notlike ('*'+$b+'*')) { [Environment]::SetEnvironmentVariable('Path', $p+';'+$b, 'User'); 'PATH updated' } else { 'PATH already ok' }" >> logs\install_claude_code.txt 2>&1
if exist "%USERPROFILE%\.local\bin\claude.exe" (echo CLAUDE_EXE_FOUND >> logs\install_claude_code.txt) else (echo CLAUDE_EXE_MISSING >> logs\install_claude_code.txt)
echo DONE >> logs\install_claude_code.txt
