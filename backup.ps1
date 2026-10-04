<#
.SYNOPSIS
    Cópia de segurança do sistema: banco de dados + PDFs guardados.

.DESCRIPTION
    Gera em APP\backups (ou na pasta -Destino):
      - gestao-db_AAAA-MM-DD_HHMM.dump   o banco inteiro (pg_dump, formato custom);
      - storage\                         os PDFs (só os novos são copiados a cada vez:
                                         o nome de cada arquivo é o hash do conteúdo,
                                         então um arquivo guardado nunca muda).
    Mantém os 20 dumps mais recentes.

    Restaurar (ver docs\producao.md):
      pg_restore --clean --if-exists -U <usuario> -d gestao-db <arquivo.dump>
      e copiar backups\storage de volta para backend\storage.

    Dica: agende este script no "Agendador de Tarefas" do Windows (1x por dia) e
    use como -Destino uma pasta de outro disco ou sincronizada com a nuvem.
#>
param([string]$Destino = (Join-Path $PSScriptRoot 'backups'))

# 'Continue' e não 'Stop': no PowerShell 5.1, com 'Stop', qualquer texto que um programa
# (pip, npm, pg_dump) escreva no stderr interrompe o script, mesmo sem erro. Os códigos
# de saída ($LASTEXITCODE) são conferidos um a um.
$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$Backend = Join-Path $PSScriptRoot 'backend'
$DumpsGuardados = 20

# Lê o backend\.env (CHAVE=valor) para usar o mesmo banco e as mesmas pastas do sistema.
$Config = @{}
Get-Content (Join-Path $Backend '.env') -Encoding UTF8 | ForEach-Object {
    if ($_ -match '^\s*([A-Z_]+)\s*=\s*(.*)$') { $Config[$Matches[1]] = $Matches[2].Trim() }
}
function Valor([string]$Chave, [string]$Padrao) {
    if ($Config[$Chave]) { return $Config[$Chave] }
    return $Padrao
}

$PastaBin = Valor 'POSTGRES_BIN_DIR' ''
if (-not $PastaBin) {
    $PastaBin = (Get-ChildItem 'C:\Program Files\PostgreSQL\*\bin\pg_dump.exe' -ErrorAction SilentlyContinue |
        Sort-Object { [int]($_.Directory.Parent.Name -replace '\D.*$', '') } -Descending | Select-Object -First 1).DirectoryName
}
$PgDump = if ($PastaBin) { Join-Path $PastaBin 'pg_dump.exe' } else { 'pg_dump' }

$Banco = Valor 'POSTGRES_DB' 'gestao-db'
$Storage = Valor 'STORAGE_DIR' './storage'
if (-not [IO.Path]::IsPathRooted($Storage)) { $Storage = Join-Path $Backend $Storage }

New-Item -ItemType Directory -Force $Destino | Out-Null
$Arquivo = Join-Path $Destino ("{0}_{1}.dump" -f $Banco, (Get-Date -Format 'yyyy-MM-dd_HHmm'))

Write-Host "Banco '$Banco' -> $Arquivo" -ForegroundColor Cyan
$env:PGPASSWORD = Valor 'POSTGRES_PASSWORD' ''
try {
    & $PgDump -h (Valor 'POSTGRES_HOST' 'localhost') -p (Valor 'POSTGRES_PORT' '5432') -U (Valor 'POSTGRES_USER' 'postgres') -F c -f $Arquivo $Banco
    if ($LASTEXITCODE -ne 0) { throw 'pg_dump falhou.' }
} finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}

Write-Host "PDFs guardados -> $(Join-Path $Destino 'storage')" -ForegroundColor Cyan
if (Test-Path $Storage) {
    # /E subpastas; /XO /XN /XC não recopia o que já existe; robocopy: códigos < 8 = sucesso.
    robocopy $Storage (Join-Path $Destino 'storage') /E /XO /XN /XC /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy falhou (código $LASTEXITCODE)." }
}

# Rotação: só os dumps mais antigos que os $DumpsGuardados mais recentes saem.
Get-ChildItem $Destino -Filter "$Banco*.dump" | Sort-Object LastWriteTime -Descending |
    Select-Object -Skip $DumpsGuardados | Remove-Item

Write-Host 'Cópia de segurança concluída.' -ForegroundColor Green
