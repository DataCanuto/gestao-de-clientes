@echo off
rem Duplo clique: liga o servidor e abre o sistema no navegador.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar.ps1" %*
