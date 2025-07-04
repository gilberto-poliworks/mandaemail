import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import io
import sqlite3
from datetime import datetime
import os

# Configuração da página
st.set_page_config(
    page_title="Sistema de Contato com Parlamentares",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
            "email": ["email", "e-mail", "email_gabinete", "email_parlamentar", "email do parlamentar", "correio eletronico"],
            "cargo": ["cargo", "tipo", "titular/suplente/efetivado"]
        }
        
        # Aplicar mapeamento
        for target_col, possible_cols in column_mapping.items():
            found = False
            for col in possible_cols:
                if col in df.columns:
                    df[target_col] = df[col]
                    found = True
                    break
            if not found and target_col == "email": # Se email não for encontrado, adicione uma coluna vazia
                df["email"] = None
            elif not found and target_col == "cargo": # Se cargo não for encontrado, defina um padrão
                df["cargo"] = "Parlamentar"
        
        # Verificar se tem as colunas essenciais
        required_cols = ["nome", "partido", "uf"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            st.error(f"Colunas obrigatórias não encontradas: {missing_cols}")
            return None
        
        # Limpar dados
        df = df.dropna(subset=["nome"])
        df["nome"] = df["nome"].str.strip()
        df["partido"] = df["partido"].str.strip()
        df["uf"] = df["uf"].str.strip()
        
        return df
        
    except Exception as e:
        st.error(f"Erro ao processar arquivo: {str(e)}")
        return None

# Define o caminho do banco de dados para ser gravável no Streamlit Cloud
DB_PATH = os.path.join(os.getcwd(), "email_history.db")

def init_database():
    """Inicializa banco de dados SQLite"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
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
    """
    )
    
    conn.commit()
    conn.close()

def save_email_history(subject, message, sender_name, sender_email, recipients_count, sent, failed):
    """Salva histórico de envio no banco"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO email_history (subject, message, sender_name, sender_email, recipients_count, sent, failed)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (subject, message, sender_name, sender_email, recipients_count, sent, failed))
    
    conn.commit()
    conn.close()

def get_email_history():
    """Recupera histórico de envios"""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM email_history ORDER BY date DESC", conn)
    conn.close()
    return df

def send_emails(recipients, subject, message, sender_name, sender_email, sender_password):
    """Envia e-mails para os destinatários selecionados"""
    sent_count = 0
    failed_count = 0
    
    # Configurar SMTP
    smtp_config = get_smtp_config(sender_email)
    
    try:
        server = smtplib.SMTP(smtp_config["server"], smtp_config["port"])
        server.starttls()
        server.login(sender_email, sender_password)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, recipient in enumerate(recipients):
            try:
                if pd.isna(recipient.get("email")) or not recipient.get("email"):
                    failed_count += 1
                    continue
                
                # Personalizar mensagem
                personalized_message = message.replace("{nome}", recipient.get("nome", ""))
                
                # Criar e-mail
                msg = MIMEMultipart()
                msg["From"] = f"{sender_name} <{sender_email}>"
                msg["To"] = recipient["email"]
                msg["Subject"] = subject
                
                # Corpo do e-mail
                body = f"""Prezado(a) {recipient.get("nome", "")},

{personalized_message}

Atenciosamente,
{sender_name}
{sender_email}
"""
                
                msg.attach(MIMEText(body, "plain", "utf-8"))
                
                # Enviar
                server.send_message(msg)
                sent_count += 1
                
                # Atualizar progresso
                progress = (i + 1) / len(recipients)
                progress_bar.progress(progress)
                status_text.text(f"Enviando... {i + 1}/{len(recipients)}")
                
            except Exception as e:
                failed_count += 1
                st.warning(f"Erro ao enviar para {recipient.get("email", "")}: {str(e)}")
        
        server.quit()
        
        # Salvar no histórico
        save_email_history(subject, message, sender_name, sender_email, 
                          len(recipients), sent_count, failed_count)
        
        return sent_count, failed_count
        
    except Exception as e:
        st.error(f"Erro na configuração do e-mail: {str(e)}")
        return 0, len(recipients)

# Inicializar banco de dados
init_database()

# Interface principal
def main():
    st.write("DEBUG: Aplicação iniciada.") # Adicione esta linha
    # Cabeçalho
    st.markdown("""
    <div class="main-header">
        <h1>🏛️ Sistema de Contato com Parlamentares</h1>
        <p>Envie mensagens personalizadas para deputados e senadores de forma simples e eficiente</p>
    </div>
    """, unsafe_allow_html=True)
    st.write("DEBUG: Cabeçalho renderizado.") # Adicione esta linha
    
    # Sidebar para navegação
    st.sidebar.title("📋 Menu")
    page = st.sidebar.selectbox("Escolha uma opção:", [
        "📤 Enviar E-mails",
        "📊 Histórico de Envios",
        "📖 Como Usar",
        "ℹ️ Sobre"
    ])
    
    if page == "📤 Enviar E-mails":
        enviar_emails_page()
    elif page == "📊 Histórico de Envios":
        historico_page()
    elif page == "📖 Como Usar":
        como_usar_page()
    elif page == "ℹ️ Sobre":
        sobre_page()

def enviar_emails_page():
    st.header("📤 Enviar E-mails para Parlamentares")
    
    # Upload de arquivo
    st.subheader("1. 📁 Importar Dados dos Parlamentares")
    
    uploaded_file = st.file_uploader(
        "Escolha uma planilha com dados dos parlamentares",
        type=["csv", "xls", "xlsx"],
        help="Formatos suportados: .csv, .xls, .xlsx. Planilhas oficiais da Câmara dos Deputados e Senado Federal."
    )
    
    if uploaded_file is not None:
        with st.spinner("Processando planilha..."):
            df = process_spreadsheet(uploaded_file)
        
        if df is not None:
            st.success(f"✅ Planilha processada com sucesso! {len(df)} parlamentares carregados.")
            
            # Garantir que a coluna 'email' exista, mesmo que vazia
            if "email" not in df.columns:
                df["email"] = None

            # Filtros
            st.subheader("2. 🔍 Filtrar Parlamentares")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                nome_filter = st.text_input("Nome:", placeholder="Digite parte do nome")
            
            with col2:
                partidos = ["Todos"] + sorted(df["partido"].dropna().unique().tolist())
                partido_filter = st.selectbox("Partido:", partidos)
            
            with col3:
                estados = ["Todos"] + sorted(df["uf"].dropna().unique().tolist())
                estado_filter = st.selectbox("Estado:", estados)
            
            with col4:
                cargos = ["Todos"] + sorted(df["cargo"].dropna().unique().tolist())
                cargo_filter = st.selectbox("Cargo:", cargos)
            
            # Aplicar filtros
            filtered_df = df.copy()
            
            if nome_filter:
                filtered_df = filtered_df[filtered_df["nome"].str.contains(nome_filter, case=False, na=False)]
            
            if partido_filter != "Todos":
                filtered_df = filtered_df[filtered_df["partido"] == partido_filter]
            
            if estado_filter != "Todos":
                filtered_df = filtered_df[filtered_df["uf"] == estado_filter]
            
            if cargo_filter != "Todos":
                filtered_df = filtered_df[filtered_df["cargo"] == cargo_filter]
            
            st.info(f"📋 {len(filtered_df)} parlamentares encontrados com os filtros aplicados")
            
            # Seleção de parlamentares
            st.subheader("3. ✅ Selecionar Destinatários")
            
            if len(filtered_df) > 0:
                # Adicionar depuração aqui
                st.write(f"DEBUG: filtered_df columns: {filtered_df.columns.tolist()}")
                st.write(f"DEBUG: filtered_df head:\n{filtered_df.head().to_string()}")

                # Mostrar tabela com seleção
                selection_df = filtered_df[["nome", "partido", "uf", "cargo"]].copy()
                
                # Garante que a coluna 'email' existe antes de tentar acessá-la
                if "email" not in filtered_df.columns:
                    filtered_df["email"] = None # Adiciona a coluna se não existir

                selection_df["email_disponivel"] = filtered_df["email"].notna() & (filtered_df["email"] != "")
                selection_df["email_disponivel"] = selection_df["email_disponivel"].map({True: "✅", False: "❌"})
                
                selected_indices = st.multiselect(
                    "Escolha os parlamentares:",
                    options=range(len(filtered_df)),
                    format_func=lambda x: f"{filtered_df.iloc[x]["nome"]} - {filtered_df.iloc[x]["partido"]}/{filtered_df.iloc[x]["uf"]} {"✅" if pd.notna(filtered_df.iloc[x].get("email")) else "❌"}"
                )
                
                if st.button("🔄 Selecionar Todos"):
                    selected_indices = list(range(len(filtered_df)))
                    st.rerun()
                
                if selected_indices:
                    selected_df = filtered_df.iloc[selected_indices]
                    st.success(f"✅ {len(selected_indices)} parlamentares selecionados")
                    
                    # Verificar e-mails
                    emails_validos = selected_df["email"].notna() & (selected_df["email"] != "")
                    emails_count = emails_validos.sum()
                    
                    if emails_count == 0:
                        st.error("❌ Nenhum dos parlamentares selecionados possui e-mail válido.")
                        return
                    elif emails_count < len(selected_indices):
                        st.warning(f"⚠️ Apenas {emails_count} dos {len(selected_indices)} parlamentares selecionados possuem e-mail válido.")
                    
                    # Composição da mensagem
                    st.subheader("4. ✉️ Compor Mensagem")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        subject = st.text_input("Assunto:", placeholder="Digite o assunto do e-mail")
                        sender_name = st.text_input("Seu Nome:", placeholder="Digite seu nome completo")
                        sender_email = st.text_input("Seu E-mail:", placeholder="Digite seu e-mail")
                    
                    with col2:
                        sender_password = st.text_input("Senha do E-mail:", type="password", 
                                                      help="Use senha de aplicativo para Gmail/Outlook")
                    
                    message = st.text_area(
                        "Mensagem:",
                        height=200,
                        placeholder="Digite sua mensagem aqui. Use {nome} para incluir o nome do parlamentar automaticamente.",
                        help="Use {nome} para personalizar a mensagem com o nome do parlamentar"
                    )
                    
                    # Prévia
                    if subject and message and sender_name:
                        st.subheader("5. 👁️ Prévia do E-mail")
                        
                        sample_recipient = selected_df.iloc[0]
                        preview_message = message.replace("{nome}", sample_recipient["nome"])
                        
                        st.markdown(f"""
                            <div class="feature-box">
                            <strong>Para:</strong> {sample_recipient["nome"]} &lt;{sample_recipient.get("email", "email@exemplo.com")}&gt;<br>
                            <strong>Assunto:</strong> {subject}<br>
                            <hr>
                            <div style="white-space: pre-wrap;">{preview_message}</div>
                            <hr>
                            <em>Atenciosamente,<br>{sender_name}</em><br>
                            <small>Este e-mail será enviado para {emails_count} parlamentar(es) com e-mail válido.</small>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Envio
                        if st.button("📧 Enviar E-mails", type="primary"):
                            if not all([subject, message, sender_name, sender_email, sender_password]):
                                st.error("❌ Por favor, preencha todos os campos obrigatórios.")
                            else:
                                # Filtrar apenas parlamentares com e-mail
                                recipients_with_email = selected_df[emails_validos].to_dict("records")
                                
                                with st.spinner("Enviando e-mails..."):
                                    sent, failed = send_emails(
                                        recipients_with_email, subject, message, 
                                        sender_name, sender_email, sender_password
                                    )
                                
                                if sent > 0:
                                    st.markdown(f"""
                                    <div class="success-box">
                                    <h4>✅ Envio Concluído!</h4>
                                    <ul>
                                    <li><strong>Enviados:</strong> {sent}</li>
                                    <li><strong>Falhas:</strong> {failed}</li>
                                    <li><strong>Total:</strong> {sent + failed}</li>
                                    </ul>
                                    </div>
                                    """, unsafe_allow_html=True)
                                else:
                                    st.error("❌ Nenhum e-mail foi enviado. Verifique suas credenciais e configurações.")
                    
                    else:
                        st.info("👆 Selecione pelo menos um parlamentar para continuar.")
                
                else:
                    st.warning("⚠️ Nenhum parlamentar encontrado com os filtros aplicados. Tente ajustar os critérios de busca.")
        
        else:
            st.info("👆 Faça upload de uma planilha para começar.")
            
            st.markdown("""
            <div class="feature-box">
            <h4>📋 Onde obter as planilhas oficiais:</h4>
            <ul>
            <li><strong>Câmara dos Deputados:</strong> <a href="https://www.camara.leg.br/internet/deputado/deputado.xls" target="_blank">deputado.xls</a></li>
            <li><strong>Senado Federal:</strong> Dados disponíveis em <a href="https://www12.senado.leg.br/dados-abertos" target="_blank">Dados Abertos do Senado</a></li>
            </ul>
            </div>
            """, unsafe_allow_html=True)

def historico_page():
    st.header("📊 Histórico de Envios")
    
    history_df = get_email_history()
    
    if len(history_df) > 0:
        st.subheader(f"📈 Total de {len(history_df)} envios realizados")
        
        # Estatísticas
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_sent = history_df["sent"].sum()
            st.metric("E-mails Enviados", total_sent)
        
        with col2:
            total_failed = history_df["failed"].sum()
            st.metric("Falhas", total_failed)
        
        with col3:
            total_recipients = history_df["recipients_count"].sum()
            st.metric("Total de Destinatários", total_recipients)
        
        with col4:
            success_rate = (total_sent / (total_sent + total_failed) * 100) if (total_sent + total_failed) > 0 else 0
            st.metric("Taxa de Sucesso", f"{success_rate:.1f}%")
        
        # Tabela de histórico
        st.subheader("📋 Detalhes dos Envios")
        
        display_df = history_df[["date", "subject", "sender_name", "recipients_count", "sent", "failed"]].copy()
        display_df["date"] = pd.to_datetime(display_df["date"]).dt.strftime("%d/%m/%Y %H:%M")
        display_df.columns = ["Data", "Assunto", "Remetente", "Destinatários", "Enviados", "Falhas"]
        
        st.dataframe(display_df, use_container_width=True)
        
        # Gráfico de envios por dia
        if len(history_df) > 1:
            st.subheader("📈 Envios por Dia")
            
            history_df["date"] = pd.to_datetime(history_df["date"])
            daily_stats = history_df.groupby(history_df["date"].dt.date).agg({
                "sent": "sum",
                "failed": "sum"
            }).reset_index()
            
            st.line_chart(daily_stats.set_index("date"))
    
    else:
        st.info("📭 Nenhum envio realizado ainda. Use a página \"Enviar E-mails\" para começar.")

def como_usar_page():
    st.header("📖 Como Usar o Sistema")
    
    st.markdown("""
    <div class="feature-box">
    <h3>🚀 Passo a Passo</h3>
    
    <h4>1. 📁 Importar Dados</h4>
    <ul>
    <li>Baixe a planilha oficial da Câmara dos Deputados ou Senado Federal</li>
    <li>Faça upload do arquivo (.csv, .xls ou .xlsx)</li>
    <li>O sistema processará automaticamente os dados</li>
    <li>Verifique se os parlamentares possuem e-mail válido (✅)</li>
    </ul>
    
    <h4>2. 🔍 Filtrar Parlamentares</h4>
    <ul>
    <li>Use os filtros por nome, partido, estado ou cargo</li>
    <li>Combine múltiplos filtros para refinar a busca</li>
    <li>Veja quantos parlamentares correspondem aos critérios</li>
    </ul>
    
    <h4>3. ✅ Selecionar Destinatários</h4>
    <ul>
    <li>Escolha individualmente os parlamentares desejados</li>
    <li>Use "Selecionar Todos" para escolher todos os filtrados</li>
    <li>Verifique se os parlamentares possuem e-mail válido (✅)</li>
    </ul>
    
    <h4>4. ✉️ Compor Mensagem</h4>
    <ul>
    <li>Preencha o assunto e a mensagem</li>
    <li>Use <code>{nome}</code> para personalizar com o nome do parlamentar</li>
    <li>Configure suas credenciais de e-mail</li>
    </ul>
    
    <h4>5. 📧 Enviar</h4>
    <ul>
    <li>Visualize a prévia antes de enviar</li>
    <li>Clique em "Enviar E-mails" para iniciar o processo</li>
    <li>Acompanhe o progresso e os resultados</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="warning-box">
    <h4>⚠️ Configuração de E-mail</h4>
    
    <h5>Gmail:</h5>
    <ol>
    <li>Ative a verificação em duas etapas</li>
    <li>Gere uma senha de aplicativo em <a href="https://myaccount.google.com/apppasswords" target="_blank">myaccount.google.com/apppasswords</a></li>
    <li>Use a senha gerada no campo "Senha do E-mail"</li>
    </ol>
    
    <h5>Outlook/Hotmail:</h5>
    <ol>
    <li>Ative a verificação em duas etapas na conta Microsoft</li>
    <li>Gere uma senha de aplicativo nas configurações de segurança</li>
    <li>Use a senha gerada na aplicação</li>
    </ol>
    </div>
    """, unsafe_allow_html=True)

def sobre_page():
    st.header("ℹ️ Sobre o Sistema")
    
    st.markdown("""
    <div class="feature-box">
    <h3>🏛️ Sistema de Contato com Parlamentares</h3>
    
    <p>Esta aplicação foi desenvolvida para facilitar a comunicação entre cidadãos e seus representantes eleitos, 
    promovendo uma democracia mais participativa e transparente.</p>
    
    <h4>✨ Funcionalidades:</h4>
    <ul>
    <li>📤 Envio de e-mails personalizados em massa</li>
    <li>📊 Processamento automático de planilhas oficiais</li>
    <li>🔍 Sistema avançado de filtros</li>
    <li>📈 Histórico completo de envios</li>
    <li>🔒 Segurança e privacidade dos dados</li>
    <li>📱 Interface responsiva e intuitiva</li>
    </ul>
    
    <h4>🛠️ Tecnologias:</h4>
    <ul>
    <li><strong>Frontend:</strong> Streamlit</li>
    <li><strong>Backend:</strong> Python</li>
    <li><strong>Banco de Dados:</strong> SQLite</li>
    <li><strong>Processamento:</strong> Pandas</li>
    </ul>
    
    <h4>🌐 Compatibilidade:</h4>
    <ul>
    <li><strong>Provedores de E-mail:</strong> Gmail, Outlook, Yahoo, UOL, Terra, IG</li>
    <li><strong>Formatos de Arquivo:</strong> .csv, .xls, .xlsx</li>
    <li><strong>Navegadores:</strong> Chrome, Firefox, Safari, Edge</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="success-box">
    <h4>🔒 Segurança e Privacidade</h4>
    <ul>
    <li>Senhas de e-mail não são armazenadas</li>
    <li>Dados dos parlamentares são públicos e oficiais</li>
    <li>Histórico fica apenas no seu computador</li>
    <li>Comunicação criptografada (HTTPS)</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="warning-box">
    <h4>📋 Uso Responsável</h4>
    <p>Esta ferramenta deve ser usada de forma responsável para comunicação legítima com representantes eleitos:</p>
    <ul>
    <li>Não envie spam ou mensagens irrelevantes</li>
    <li>Seja respeitoso na comunicação</li>
    <li>Use apenas dados públicos oficiais</li>
    <li>Respeite os limites dos provedores de e-mail</li>
    <li>Mantenha o tom civilizado nas mensagens</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

