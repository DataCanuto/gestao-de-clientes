<#
.SYNOPSIS
    Instala ou atualiza o sistema Gestão de Clientes e Documentos neste computador (Windows).

.DESCRIPTION
    Pode ser executado de novo a qualquer momento (por exemplo, depois de
    atualizar o código): cada passo só faz o que ainda falta.

    1. confere Python, Node.js, PostgreSQL e Tesseract;
    2. cria o ambiente Python (backend\.venv) e instala as dependências;
    3. Smart App Control: se o Windows bloquear as extensões compiladas do
       SQLAlchemy, instala a versão pura em Python (mesma versão);
    4. cria o backend\.env na primeira vez (pergunta usuário e senha do PostgreSQL);
    5. cria o banco, se preciso, e aplica as migrations;
    6. compila o frontend (frontend\dist), que o servidor passa a servir.

    Uso:  clique com o botão direito > "Executar com o PowerShell"
     ou:  powershell -ExecutionPolicy Bypass -File instalar.ps1
#>

# 'Continue' e não 'Stop': no PowerShell 5.1, com 'Stop', qualquer texto que um programa
# (pip, npm, pg_dump) escreva no stderr interrompe o script, mesmo sem erro. Os códigos
# de saída ($LASTEXITCODE) são conferidos um a um.
$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:PYTHONUTF8 = '1'

$Raiz = $PSScriptRoot
$Backend = Join-Path $Raiz 'backend'
$Frontend = Join-Path $Raiz 'frontend'
$VenvPython = Join-Path $Backend '.venv\Scripts\python.exe'

function Passo([string]$Texto) { Write-Host "`n==> $Texto" -ForegroundColor Cyan }
function Ok([string]$Texto) { Write-Host "    $Texto" -ForegroundColor Green }
function Atencao([string]$Texto) { Write-Host "    ATENÇÃO: $Texto" -ForegroundColor Yellow }
function Falhar([string]$Texto) {
    Write-Host "`nERRO: $Texto" -ForegroundColor Red
    Read-Host 'Pressione Enter para sair'
    exit 1
}
function ExigirSucesso([string]$Mensagem) { if ($LASTEXITCODE -ne 0) { Falhar $Mensagem } }

# ---------------------------------------------------------------- 1. pré-requisitos
Passo 'Conferindo os programas necessários'

$PythonBase = $null
foreach ($candidato in @(@('py', '-3.14'), @('py', '-3.13'), @('py', '-3.12'), @('python'))) {
    if (Get-Command $candidato[0] -ErrorAction SilentlyContinue) {
        $argumentos = @($candidato | Select-Object -Skip 1) + @('-c', 'import sys; print(sys.version_info >= (3, 12))')
        $saida = & $candidato[0] @argumentos 2>$null
        if ($saida -eq 'True') { $PythonBase = $candidato; break }
    }
}
if (-not (Test-Path $VenvPython) -and -not $PythonBase) {
    Falhar 'Python 3.12 ou mais novo não encontrado. Instale em https://www.python.org/downloads/ e rode de novo.'
}
Ok 'Python encontrado.'

$TemNode = [bool](Get-Command npm -ErrorAction SilentlyContinue)
if ($TemNode) { Ok 'Node.js encontrado.' }
elseif (Test-Path (Join-Path $Frontend 'dist\index.html')) { Atencao 'Node.js não encontrado: o frontend já compilado será usado.' }
else { Falhar 'Node.js não encontrado (necessário para compilar a tela). Instale em https://nodejs.org e rode de novo.' }

$PastaPostgres = Get-ChildItem 'C:\Program Files\PostgreSQL\*\bin\libpq.dll' -ErrorAction SilentlyContinue |
    Sort-Object { [int]($_.Directory.Parent.Name -replace '\D.*$', '') } -Descending | Select-Object -First 1
if ($PastaPostgres) { Ok "PostgreSQL encontrado em $($PastaPostgres.DirectoryName)." }
else { Atencao 'PostgreSQL não encontrado em C:\Program Files\PostgreSQL. Instale-o (https://www.postgresql.org/download/windows/) ou informe POSTGRES_BIN_DIR no backend\.env.' }

$Tesseract = 'C:\Program Files\Tesseract-OCR\tesseract.exe'
if ((Test-Path $Tesseract) -or (Get-Command tesseract -ErrorAction SilentlyContinue)) { Ok 'Tesseract (OCR) encontrado.' }
else { Atencao 'Tesseract não encontrado: as Notas Fiscais (escaneadas) não serão lidas. Instale em https://github.com/UB-Mannheim/tesseract/wiki' }

# ---------------------------------------------------------------- 2. ambiente Python
Passo 'Preparando o ambiente Python (backend\.venv)'
if (-not (Test-Path $VenvPython)) {
    $argumentos = @($PythonBase | Select-Object -Skip 1) + @('-m', 'venv', (Join-Path $Backend '.venv'))
    & $PythonBase[0] @argumentos
    ExigirSucesso 'não foi possível criar o ambiente Python.'
}
& $VenvPython -m pip install --disable-pip-version-check -q -r (Join-Path $Backend 'requirements.txt')
ExigirSucesso 'falha ao instalar as dependências Python.'
Ok 'Dependências instaladas.'

# ---------------------------------------------------------------- 3. Smart App Control
& $VenvPython -c 'import sqlalchemy.util' 2>$null
if ($LASTEXITCODE -ne 0) {
    Atencao 'O Windows bloqueou as extensões compiladas do SQLAlchemy (Smart App Control). Instalando a versão pura em Python...'
    $versao = (Select-String -Path (Join-Path $Backend 'requirements.txt') -Pattern '^SQLAlchemy==([\d.]+)').Matches[0].Groups[1].Value
    $versaoPython = & $VenvPython -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")'
    $temporaria = Join-Path $env:TEMP "sqlalchemy-puro-$versao"
    & $VenvPython -m pip download --disable-pip-version-check -q --no-deps --only-binary=:all: --platform any --implementation py --python-version $versaoPython -d $temporaria "SQLAlchemy==$versao"
    ExigirSucesso 'não foi possível baixar o SQLAlchemy puro.'
    $roda = Get-ChildItem $temporaria -Filter '*py3-none-any.whl' | Select-Object -First 1
    & $VenvPython -m pip install --disable-pip-version-check -q --no-deps --force-reinstall $roda.FullName
    ExigirSucesso 'não foi possível instalar o SQLAlchemy puro.'
    & $VenvPython -c 'import sqlalchemy.util'
    ExigirSucesso 'o SQLAlchemy continua sem carregar.'
    Ok 'SQLAlchemy (puro) instalado.'
}

# ---------------------------------------------------------------- 4. configuração (.env)
Passo 'Configuração (backend\.env)'
$ArquivoEnv = Join-Path $Backend '.env'
if (Test-Path $ArquivoEnv) {
    Ok 'backend\.env já existe (mantido como está).'
} else {
    $usuario = Read-Host '    Usuário do PostgreSQL (ex.: postgres)'
    $senhaSegura = Read-Host '    Senha do PostgreSQL' -AsSecureString
    $senha = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($senhaSegura))
    $conteudo = Get-Content (Join-Path $Backend '.env.example') -Encoding UTF8 | ForEach-Object {
        if ($_ -match '^POSTGRES_USER=') { "POSTGRES_USER=$usuario" }
        elseif ($_ -match '^POSTGRES_PASSWORD=') { "POSTGRES_PASSWORD=$senha" }
        else { $_ }
    }
    # UTF-8 sem BOM: é o que o pydantic-settings espera.
    [IO.File]::WriteAllLines($ArquivoEnv, $conteudo, (New-Object Text.UTF8Encoding $false))
    Ok 'backend\.env criado. Para mudar pastas ou senha depois, edite esse arquivo.'
}

# ---------------------------------------------------------------- 5. banco de dados
Passo 'Banco de dados (criação e migrations)'
Push-Location $Backend
try {
    & $VenvPython -m scripts.preparar_banco
    ExigirSucesso 'não foi possível preparar o banco. Confira o PostgreSQL e o backend\.env.'
} finally { Pop-Location }

# ---------------------------------------------------------------- 6. frontend
if ($TemNode) {
    Passo 'Compilando a tela (frontend\dist)'
    Push-Location $Frontend
    try {
        npm install --no-audit --no-fund --loglevel=error
        ExigirSucesso 'falha ao instalar as dependências do frontend.'
        npm run build
        ExigirSucesso 'falha ao compilar o frontend.'
    } finally { Pop-Location }
}

Write-Host "`nPronto! Para abrir o sistema, clique duas vezes em 'Iniciar Relatorio.bat'." -ForegroundColor Green
Read-Host 'Pressione Enter para sair'
