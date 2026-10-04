@echo off
rem Copia de seguranca do banco e dos PDFs em APPackups.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0backup.ps1" %*
pause
