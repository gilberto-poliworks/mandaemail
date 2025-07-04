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
        
        # Remover colunas desnecessárias
        unnecessary_cols = [
            "endereço", "anexo", "endereço (continuação)", "gabinete", 
            "endereço (complemento)", "fax", "mês aniversário", "dia aniversário", 
            "tratamento", "nome civil"
        ]
        df = df.drop(columns=[col for col in unnecessary_cols if col in df.columns])

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
    """)
    
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
    # Cabeçalho
    st.markdown("""
    <div class="main-header">
        <h1>🏛️ Sistema de Contato com Parlamentares</h1>
        <p>Envie mensagens personalizadas para deputados e senadores de forma simples e eficiente</p>
    </div>
    """, unsafe_allow_html=True)
    
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
            
            # --- INÍCIO DA DEPURACÃO --- 
            st.write("DEBUG: Colunas em filtered_df antes da linha 336:", filtered_df.columns.tolist())
            st.write("DEBUG: filtered_df.head() antes da linha 336:")
            st.dataframe(filtered_df.head())
            # --- FIM DA DEPURACÃO --- 

            # Seleção de parlamentares
            st.subheader("3. ✅ Selecionar Destinatários")
            
            if len(filtered_df) > 0:
                # Colunas a serem exibidas na tabela de seleção
                display_cols = ["nome", "partido", "uf", "cargo", "email"]
                # Garante que todas as colunas de display existam no filtered_df
                for col in display_cols:
                    if col not in filtered_df.columns:
                        filtered_df[col] = None # Adiciona a coluna se não existir

                # Cria a selection_df com as colunas desejadas
                selection_df = filtered_df[display_cols].copy()
                
                selection_df["email_disponivel"] = selection_df["email"].notna() & (selection_df["email"] != "")
                selection_df["email_disponivel"] = selection_df["email_disponivel"].map({True: "✅", False: "❌"})
                
                # Renomeia colunas para exibição
                selection_df = selection_df.rename(columns={
                    "nome": "Nome",
                    "partido": "Partido",
                    "uf": "UF",
                    "cargo": "Cargo",
                    "email_disponivel": "E-mail Válido"
                })
                
                # Remove a coluna de email original da exibição se não for mais necessária
                if "email" in selection_df.columns:
                    selection_df = selection_df.drop(columns=["email"])

                # Exibe a tabela com checkboxes
                st.dataframe(selection_df, use_container_width=True, hide_index=True)

                # Gerencia a seleção com checkboxes
                selected_parlamentares = []
                # Adiciona um estado para controlar a seleção de todos
                if 'select_all_checkbox' not in st.session_state:
                    st.session_state.select_all_checkbox = False

                col_select_all, col_clear_selection = st.columns([0.2, 0.8])

                with col_select_all:
                    select_all_button = st.checkbox("Selecionar Todos", value=st.session_state.select_all_checkbox, key="master_checkbox")
                    if select_all_button:
                        st.session_state.select_all_checkbox = True
                    else:
                        st.session_state.select_all_checkbox = False

                with col_clear_selection:
                    if st.button("Limpar Seleção"):
                        st.session_state.select_all_checkbox = False
                        st.session_state.selected_rows = [] # Limpa as linhas selecionadas
                        st.rerun()

                # Inicializa st.session_state.selected_rows se não existir
                if 'selected_rows' not in st.session_state:
                    st.session_state.selected_rows = []

                # Se o botão 'Selecionar Todos' foi clicado, preenche selected_rows
                if st.session_state.select_all_checkbox:
                    st.session_state.selected_rows = list(range(len(filtered_df)))

                # Cria checkboxes individuais para cada parlamentar
                for i, row in filtered_df.iterrows():
                    is_selected = i in st.session_state.selected_rows
                    checkbox_key = f"checkbox_{i}"
                    # Adiciona um callback para atualizar selected_rows quando o checkbox é clicado
                    if st.checkbox(f"{row["nome"]} - {row["partido"]}/{row["uf"]}", value=is_selected, key=checkbox_key, on_change=lambda i=i: update_selected_rows(i)):
                        pass # A atualização é feita no callback

                def update_selected_rows(index):
                    if index in st.session_state.selected_rows:
                        st.session_state.selected_rows.remove(index)
                    else:
                        st.session_state.selected_rows.append(index)

                selected_parlamentares = filtered_df.iloc[st.session_state.selected_rows].to_dict('records')

                if selected_parlamentares:
                    selected_df = pd.DataFrame(selected_parlamentares)
                    st.success(f"✅ {len(selected_df)} parlamentares selecionados")
                    
                    # Verificar e-mails
                    # A validação de e-mails deve ser feita na coluna 'email' que já foi mapeada
                    emails_validos = selected_df["email"].apply(lambda x: isinstance(x, str) and "@" in x and "." in x)
                    emails_count = emails_validos.sum()
                    
                    if emails_count == 0:
                        st.error("❌ Nenhum dos parlamentares selecionados possui e-mail válido.")
                        return
                    elif emails_count < len(selected_df):
                        st.warning(f"⚠️ Apenas {emails_count} dos {len(selected_df)} parlamentares selecionados possuem e-mail válido.")
                    
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
                                        <li>E-mails enviados com sucesso: {sent}</li>
                                        <li>E-mails com falha: {failed}</li>
                                    </ul>
                                    </div>
                                    """, unsafe_allow_html=True)
                                else:
                                    st.error("❌ Falha no envio de e-mails. Verifique suas credenciais e tente novamente.")
                                
                                # Atualizar histórico
                                st.subheader("Histórico de Envios Recente:")
                                st.dataframe(get_email_history())


def historico_page():
    st.header("📊 Histórico de Envios")
    st.write("Aqui você pode visualizar o histórico de todos os e-mails enviados.")
    
    history_df = get_email_history()
    if not history_df.empty:
        st.dataframe(history_df)
    else:
        st.info("Nenhum e-mail foi enviado ainda.")

def como_usar_page():
    st.header("📖 Como Usar")
    st.markdown("""
    Este aplicativo permite que você envie e-mails personalizados para parlamentares brasileiros.

    **Passo a passo:**

    1.  **Importar Dados:** Faça o upload de uma planilha (.csv, .xls, .xlsx) contendo os dados dos parlamentares. O aplicativo tentará identificar automaticamente as colunas de nome, partido, UF, cargo e e-mail.
    2.  **Filtrar:** Use os filtros de nome, partido, estado e cargo para encontrar os parlamentares desejados.
    3.  **Selecionar Destinatários:** Selecione os parlamentares para os quais deseja enviar o e-mail. Você pode usar a opção **"Selecionar Todos"** para selecionar todos os parlamentares filtrados ou selecionar individualmente.
    4.  **Compor Mensagem:** Escreva o assunto e o corpo da mensagem. Use `{nome}` no corpo da mensagem para que o nome do parlamentar seja inserido automaticamente.
    5.  **Prévia e Envio:** Visualize a prévia do e-mail e, quando estiver pronto, clique em **"Enviar E-mails"**.

    **Observações:**

    *   Para enviar e-mails, você precisará fornecer seu nome, e-mail e senha. Para serviços como Gmail e Outlook, pode ser necessário gerar uma **"senha de aplicativo"** específica para uso em aplicativos de terceiros, em vez da sua senha principal. Consulte a documentação do seu provedor de e-mail para mais detalhes.
    *   O histórico de envios é armazenado localmente no navegador e será resetado se você limpar os dados do site ou se o Streamlit Cloud reiniciar a aplicação (o que acontece periodicamente).
    """, unsafe_allow_html=True)

def sobre_page():
    st.header("ℹ️ Sobre")
    st.markdown("""
    Este aplicativo foi desenvolvido para facilitar a comunicação entre cidadãos e parlamentares, permitindo o envio de mensagens personalizadas de forma eficiente.

    **Recursos:**

    *   Importação de dados de planilhas (.xls, .xlsx, .csv)
    *   Filtros por nome, partido, UF e cargo
    *   Seleção de múltiplos destinatários
    *   Personalização automática de e-mails
    *   Suporte a diversos provedores de e-mail (Gmail, Outlook, Yahoo, etc.)
    *   Histórico de envios

    **Desenvolvido por:** Manus AI
    **Versão:** 1.0
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

