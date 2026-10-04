<#
.SYNOPSIS
    Liga o servidor do sistema Gestão de Clientes e Documentos e abre o sistema no navegador.

.DESCRIPTION
    - atualiza a estrutura do banco, se o código mudou (alembic upgrade head);
    - liga o servidor em http://127.0.0.1:8000 (API + tela);
    - abre o navegador quando o servidor responder.
    Para desligar: feche esta janela (ou Ctrl+C).

    -Rede    aceita acessos de outros computadores da rede (ATENÇÃO: o sistema
             não tem senha; use só numa rede de confiança).
    -Porta   outra porta, se a 8000 estiver ocupada.
#>
param(
    [int]$Porta = 8000,
    [switch]$Rede,
    [switch]$SemNavegador
)

# 'Continue' e não 'Stop': no PowerShell 5.1, com 'Stop', qualquer texto que um programa
# (pip, npm, pg_dump) escreva no stderr interrompe o script, mesmo sem erro. Os códigos
# de saída ($LASTEXITCODE) são conferidos um a um.
$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:PYTHONUTF8 = '1'
$Host.UI.RawUI.WindowTitle = 'Gestão de Clientes e Documentos - servidor'

$Backend = Join-Path $PSScriptRoot 'backend'
$VenvPython = Join-Path $Backend '.venv\Scripts\python.exe'
$Endereco = "http://127.0.0.1:$Porta"

if (-not (Test-Path $VenvPython)) {
    Write-Host 'O sistema ainda não foi instalado. Rode primeiro o instalar.ps1.' -ForegroundColor Red
    Read-Host 'Pressione Enter para sair'
    exit 1
}

# Já está ligado? Então só abre o navegador.
if (Get-NetTCPConnection -LocalPort $Porta -State Listen -ErrorAction SilentlyContinue) {
    Write-Host "O servidor já está ligado em $Endereco." -ForegroundColor Yellow
    if (-not $SemNavegador) { Start-Process $Endereco }
    exit 0
}

# Log em arquivo (backend\logs\app.log), a não ser que o .env já defina outro.
$ArquivoEnv = Join-Path $Backend '.env'
if (-not $env:ARQUIVO_LOG -and -not (Select-String -Path $ArquivoEnv -Pattern '^\s*ARQUIVO_LOG=' -Quiet -ErrorAction SilentlyContinue)) {
    $env:ARQUIVO_LOG = './logs/app.log'
}

Push-Location $Backend
try {
    Write-Host 'Conferindo o banco de dados...' -ForegroundColor Cyan
    & $VenvPython -m scripts.preparar_banco
    if ($LASTEXITCODE -ne 0) {
        Read-Host 'Pressione Enter para sair'
        exit 1
    }

    if (-not $SemNavegador) {
        # Um "job" em segundo plano espera o servidor responder e abre o navegador.
        Start-Job -ArgumentList $Endereco -ScriptBlock {
            param($url)
            for ($i = 0; $i -lt 60; $i++) {
                try {
                    Invoke-WebRequest "$url/api/v1/saude" -UseBasicParsing -TimeoutSec 2 | Out-Null
                    Start-Process $url
                    return
                } catch { Start-Sleep -Seconds 1 }
            }
        } | Out-Null
    }

    $Interface = '127.0.0.1'
    if ($Rede) {
        $Interface = '0.0.0.0'
        Write-Host 'ATENÇÃO: acessível pela rede e SEM senha. Use só numa rede de confiança.' -ForegroundColor Yellow
    }
    Write-Host "`nSistema no ar em $Endereco  (para desligar, feche esta janela)`n" -ForegroundColor Green
    # --no-access-log: a tela consulta o progresso a cada 2 s; o log ficaria ilegível.
    & $VenvPython -m uvicorn app.main:app --host $Interface --port $Porta --no-access-log
} finally {
    Pop-Location
}
