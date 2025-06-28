@echo off
REM Script de instalação do Sistema de Contato com Parlamentares para Windows
REM Execute este script para configurar automaticamente a aplicação

echo === Sistema de Contato com Parlamentares ===
echo Iniciando instalação...

REM Verificar se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python não encontrado. Por favor, instale Python 3.8 ou superior.
    echo Baixe em: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python encontrado
python --version

REM Criar ambiente virtual se não existir
if not exist "venv" (
    echo 📦 Criando ambiente virtual...
    python -m venv venv
)

REM Ativar ambiente virtual
echo 🔧 Ativando ambiente virtual...
call venv\Scripts\activate.bat

REM Instalar dependências
echo 📥 Instalando dependências...
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Criar diretórios necessários
if not exist "src\database" mkdir src\database

REM Verificar instalação
echo 🧪 Verificando instalação...
python -c "import flask, pandas, sqlalchemy; print('✅ Todas as dependências instaladas com sucesso!')"

echo.
echo 🎉 Instalação concluída!
echo.
echo Para executar a aplicação:
echo 1. venv\Scripts\activate.bat
echo 2. python src\main.py
echo 3. Acesse http://localhost:5000
echo.
echo 📖 Consulte o MANUAL_USUARIO.pdf para instruções detalhadas.
pause

