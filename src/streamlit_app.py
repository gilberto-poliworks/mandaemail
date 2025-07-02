import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import io
import sqlite3
from datetime import datetime
import os
st.write("DEBUG: Aplicação iniciada.")
# Configuração da página
st.set_page_config(
    page_title="Sistema de Contato com Parlamentares",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.write("DEBUG: Função main() iniciada.")
# CSS customizado
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    .feature-box {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #2a5298;
        margin: 1rem 0;
    }
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .warning-box {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)
st.write("DEBUG: Cabeçalho renderizado")
# Funções auxiliares
def get_smtp_config(email):
    """Retorna configuração SMTP baseada no provedor de e-mail"""
    domain = email.split("@")[1].lower()
    
    smtp_configs = {
        "gmail.com": {"server": "smtp.gmail.com", "port": 587},
        "outlook.com": {"server": "smtp-mail.outlook.com", "port": 587},
        "hotmail.com": {"server": "smtp-mail.outlook.com", "port": 587},
        "live.com": {"server": "smtp-mail.outlook.com", "port": 587},
        "yahoo.com": {"server": "smtp.mail.yahoo.com", "port": 587},
        "yahoo.com.br": {"server": "smtp.mail.yahoo.com", "port": 587},
        "uol.com.br": {"server": "smtps.uol.com.br", "port": 587},
        "terra.com.br": {"server": "smtp.terra.com.br", "port": 587},
        "ig.com.br": {"server": "smtp.ig.com.br", "port": 587},
    }
    
    return smtp_configs.get(domain, {"server": "smtp.gmail.com", "port": 587})

def process_spreadsheet(file):
    """Processa planilha e retorna DataFrame"""
    try:
        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
        elif file.name.endswith((".xls", ".xlsx")):
            df = pd.read_excel(file)
        else:
            st.error("Formato de arquivo não suportado. Use .csv, .xls ou .xlsx")
            return None
        
        # Normalizar nomes das colunas
        df.columns = df.columns.str.lower().str.strip()
        
        # Mapear colunas comuns
        column_mapping = {
            "nome": ["nome", "nome_parlamentar", "nome completo", "nome parlamentar"],
            "partido": ["partido", "sigla_partido", "siglapartido"],
            "uf": ["uf", "estado", "sigla_uf"],
            "email": ["email", "e-mail", "email_gabinete"],
            "cargo": ["cargo", "tipo"]
        }
        
        # Aplicar mapeamento
        for target_col, possible_cols in column_mapping.items():
            for col in possible_cols:
                if col in df.columns:
                    df[target_col] = df[col]
                    break
        
        # Verificar se tem as colunas essenciais
        required_cols = ["nome", "partido", "uf"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            st.error(f"Colunas obrigatórias não encontradas: {missing_cols}")
            return None
        
        # Adicionar cargo se não existir
        if "cargo" not in df.columns:
            df["cargo"] = "Deputado"  # Assumir deputado por padrão
        
        # Limpar dados
        df = df.dropna(subset=["nome"])
        df["nome"] = df["nome"].str.strip()
        df["partido"] = df["partido"].str.strip()
        df["uf"] = df["uf"].str.strip()
        
        return df
        
    except Exception as e:
        st.error(f"Erro ao processar arquivo: {str(e)}")
        return None

def init_database():
    st.write("DEBUG: Iniciando base de dados.")
    """Inicializa banco de dados SQLite"""
    conn = sqlite3.connect("email_history.db")
    cursor = conn.cursor()
    st.write("DEBUG: Conexão com banco estabelecida")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            subject TEXT NOT NULL,
            message TEXT NOT NULL,
            sender_name TEXT NOT NULL,
            sender_email TEXT NOT NULL,
            recipients_count INTEGER NOT NULL,
            sent INTEGER NOT NULL,
            failed INTEGER NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()
