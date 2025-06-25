#!/bin/bash

# Script de instalação do Sistema de Contato com Parlamentares
# Execute este script para configurar automaticamente a aplicação

echo "=== Sistema de Contato com Parlamentares ==="
echo "Iniciando instalação..."

# Verificar se Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado. Por favor, instale Python 3.8 ou superior."
    exit 1
fi

echo "✅ Python encontrado: $(python3 --version)"

# Criar ambiente virtual se não existir
if [ ! -d "venv" ]; then
    echo "📦 Criando ambiente virtual..."
    python3 -m venv venv
fi

# Ativar ambiente virtual
echo "🔧 Ativando ambiente virtual..."
source venv/bin/activate

# Instalar dependências
echo "📥 Instalando dependências..."
pip install --upgrade pip
pip install -r requirements.txt

# Criar diretórios necessários
mkdir -p src/database

# Verificar instalação
echo "🧪 Verificando instalação..."
python3 -c "import flask, pandas, sqlalchemy; print('✅ Todas as dependências instaladas com sucesso!')"

echo ""
echo "🎉 Instalação concluída!"
echo ""
echo "Para executar a aplicação:"
echo "1. source venv/bin/activate"
echo "2. python src/main.py"
echo "3. Acesse http://localhost:5000"
echo ""
echo "📖 Consulte o MANUAL_USUARIO.pdf para instruções detalhadas."

