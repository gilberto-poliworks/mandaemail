from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import pandas as pd
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.models.parlamentar import db, Parlamentar, EmailHistory
import tempfile

parlamentar_bp = Blueprint('parlamentar', __name__)

ALLOWED_EXTENSIONS = {'xls', 'xlsx', 'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_camara_data(df):
    """Processa dados da planilha da Câmara dos Deputados"""
    parlamentares = []
    
    for _, row in df.iterrows():
        try:
            parlamentar = {
                'nome': str(row.get('Nome Parlamentar', '')).strip(),
                'partido': str(row.get('Partido', '')).strip(),
                'uf': str(row.get('UF', '')).strip(),
                'cargo': 'Deputado',
                'email': str(row.get('Correio Eletrônico', '')).strip(),
                'telefone': str(row.get('Telefone', '')).strip(),
                'gabinete': str(row.get('Gabinete', '')).strip(),
                'endereco': f"{row.get('Endereço', '')} {row.get('Endereço (continuação)', '')} {row.get('Endereço (complemento)', '')}".strip()
            }
            
            # Validar se tem nome e pelo menos um contato
            if parlamentar['nome'] and (parlamentar['email'] or parlamentar['telefone']):
                parlamentares.append(parlamentar)
        except Exception as e:
            print(f"Erro ao processar linha: {e}")
            continue
    
    return parlamentares

def process_senado_data(df):
    """Processa dados do Senado Federal"""
    parlamentares = []
    
    for _, row in df.iterrows():
        try:
            parlamentar = {
                'nome': str(row.get('Nome', '')).strip(),
                'partido': str(row.get('Partido', '')).strip(),
                'uf': str(row.get('UF', '')).strip(),
                'cargo': 'Senador',
                'email': str(row.get('Correio Eletrônico', '')).strip(),
                'telefone': str(row.get('Telefones', '')).strip(),
                'gabinete': '',
                'endereco': ''
            }
            
            # Validar se tem nome e pelo menos um contato
            if parlamentar['nome'] and (parlamentar['email'] or parlamentar['telefone']):
                parlamentares.append(parlamentar)
        except Exception as e:
            print(f"Erro ao processar linha: {e}")
            continue
    
    return parlamentares

@parlamentar_bp.route('/upload-spreadsheet', methods=['POST'])
def upload_spreadsheet():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Formato de arquivo não suportado'}), 400
        
        # Salvar arquivo temporariamente
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            file.save(tmp_file.name)
            
            try:
                # Ler arquivo baseado na extensão
                if file.filename.lower().endswith('.csv'):
                    df = pd.read_csv(tmp_file.name, encoding='utf-8')
                elif file.filename.lower().endswith('.xls'):
                    df = pd.read_excel(tmp_file.name, engine='xlrd')
                else:
                    df = pd.read_excel(tmp_file.name, engine='openpyxl')
                
                # Limpar dados existentes
                Parlamentar.query.delete()
                db.session.commit()
                
                # Detectar tipo de planilha e processar
                parlamentares_data = []
                
                # Verificar se é planilha da Câmara (tem coluna 'Nome Parlamentar')
                if 'Nome Parlamentar' in df.columns:
                    parlamentares_data = process_camara_data(df)
                # Verificar se é planilha do Senado (tem coluna 'Nome' e 'Partido')
                elif 'Nome' in df.columns and 'Partido' in df.columns:
                    parlamentares_data = process_senado_data(df)
                else:
                    # Tentar detectar automaticamente baseado nas colunas
                    columns = [col.lower() for col in df.columns]
                    if any('nome' in col for col in columns):
                        # Mapear colunas genéricas
                        for _, row in df.iterrows():
                            try:
                                parlamentar = {
                                    'nome': '',
                                    'partido': '',
                                    'uf': '',
                                    'cargo': 'Parlamentar',
                                    'email': '',
                                    'telefone': '',
                                    'gabinete': '',
                                    'endereco': ''
                                }
                                
                                # Tentar mapear colunas automaticamente
                                for col in df.columns:
                                    col_lower = col.lower()
                                    value = str(row[col]).strip()
                                    
                                    if 'nome' in col_lower:
                                        parlamentar['nome'] = value
                                    elif 'partido' in col_lower:
                                        parlamentar['partido'] = value
                                    elif 'uf' in col_lower or 'estado' in col_lower:
                                        parlamentar['uf'] = value
                                    elif 'email' in col_lower or 'eletrônico' in col_lower:
                                        parlamentar['email'] = value
                                    elif 'telefone' in col_lower or 'fone' in col_lower:
                                        parlamentar['telefone'] = value
                                    elif 'gabinete' in col_lower:
                                        parlamentar['gabinete'] = value
                                
                                if parlamentar['nome']:
                                    parlamentares_data.append(parlamentar)
                            except Exception as e:
                                continue
                
                if not parlamentares_data:
                    return jsonify({'error': 'Não foi possível processar a planilha. Verifique se o formato está correto.'}), 400
                
                # Salvar no banco de dados
                for data in parlamentares_data:
                    parlamentar = Parlamentar(**data)
                    db.session.add(parlamentar)
                
                db.session.commit()
                
                # Retornar dados para o frontend
                result_data = [p.to_dict() for p in Parlamentar.query.all()]
                
                return jsonify({
                    'message': f'{len(result_data)} parlamentares carregados com sucesso',
                    'data': result_data
                })
                
            finally:
                # Limpar arquivo temporário
                os.unlink(tmp_file.name)
                
    except Exception as e:
        return jsonify({'error': f'Erro ao processar arquivo: {str(e)}'}), 500

@parlamentar_bp.route('/send-emails', methods=['POST'])
def send_emails():
    try:
        data = request.get_json()
        
        subject = data.get('subject')
        message = data.get('message')
        sender_name = data.get('sender_name')
        sender_email = data.get('sender_email')
        sender_password = data.get('sender_password')
        recipients = data.get('recipients', [])
        
        if not all([subject, message, sender_name, sender_email, sender_password]):
            return jsonify({'error': 'Todos os campos são obrigatórios'}), 400
        
        if not recipients:
            return jsonify({'error': 'Nenhum destinatário selecionado'}), 400
        
        sent_count = 0
        failed_count = 0
        
        # Detectar provedor de e-mail e configurar SMTP
        smtp_config = get_smtp_config(sender_email)
        
        try:
            server = smtplib.SMTP(smtp_config['server'], smtp_config['port'])
            server.starttls()
            server.login(sender_email, sender_password)
        except Exception as e:
            return jsonify({'error': f'Erro na autenticação do e-mail: {str(e)}. Verifique suas credenciais e se a autenticação de dois fatores está configurada corretamente.'}), 400
        
        # Enviar e-mails
        for recipient in recipients:
            try:
                if not recipient.get('email'):
                    failed_count += 1
                    continue
                
                # Personalizar mensagem
                personalized_message = message.replace('{nome}', recipient.get('nome', ''))
                
                # Criar e-mail
                msg = MIMEMultipart()
                msg['From'] = f"{sender_name} <{sender_email}>"
                msg['To'] = recipient['email']
                msg['Subject'] = subject
                
                # Corpo do e-mail
                body = f"""Prezado(a) {recipient.get('nome', '')},

{personalized_message}

Atenciosamente,
{sender_name}
{sender_email}
"""
                
                msg.attach(MIMEText(body, 'plain', 'utf-8'))
                
                # Enviar
                server.send_message(msg)
                sent_count += 1
                
            except Exception as e:
                print(f"Erro ao enviar para {recipient.get('email', '')}: {e}")
                failed_count += 1
        
        server.quit()
        
        # Salvar no histórico
        history = EmailHistory(
            subject=subject,
            message=message,
            sender_name=sender_name,
            sender_email=sender_email,
            recipients_count=len(recipients),
            sent=sent_count,
            failed=failed_count
        )
        db.session.add(history)
        db.session.commit()
        
        return jsonify({
            'message': 'Envio concluído',
            'sent': sent_count,
            'failed': failed_count,
            'total': len(recipients)
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao enviar e-mails: {str(e)}'}), 500

def get_smtp_config(email):
    """Retorna configuração SMTP baseada no provedor de e-mail"""
    domain = email.split('@')[1].lower()
    
    smtp_configs = {
        'gmail.com': {'server': 'smtp.gmail.com', 'port': 587},
        'outlook.com': {'server': 'smtp-mail.outlook.com', 'port': 587},
        'hotmail.com': {'server': 'smtp-mail.outlook.com', 'port': 587},
        'live.com': {'server': 'smtp-mail.outlook.com', 'port': 587},
        'yahoo.com': {'server': 'smtp.mail.yahoo.com', 'port': 587},
        'yahoo.com.br': {'server': 'smtp.mail.yahoo.com', 'port': 587},
        'uol.com.br': {'server': 'smtps.uol.com.br', 'port': 587},
        'terra.com.br': {'server': 'smtp.terra.com.br', 'port': 587},
        'ig.com.br': {'server': 'smtp.ig.com.br', 'port': 587},
    }
    
    return smtp_configs.get(domain, {'server': 'smtp.gmail.com', 'port': 587})

@parlamentar_bp.route('/email-history', methods=['GET'])
def get_email_history():
    try:
        history = EmailHistory.query.order_by(EmailHistory.date.desc()).limit(50).all()
        return jsonify([h.to_dict() for h in history])
    except Exception as e:
        return jsonify({'error': f'Erro ao carregar histórico: {str(e)}'}), 500

@parlamentar_bp.route('/parlamentares', methods=['GET'])
def get_parlamentares():
    try:
        parlamentares = Parlamentar.query.all()
        return jsonify([p.to_dict() for p in parlamentares])
    except Exception as e:
        return jsonify({'error': f'Erro ao carregar parlamentares: {str(e)}'}), 500

