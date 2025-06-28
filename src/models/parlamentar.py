from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Parlamentar(db.Model):
    __tablename__ = 'parlamentares'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    partido = db.Column(db.String(50))
    uf = db.Column(db.String(2))
    cargo = db.Column(db.String(50))  # Deputado ou Senador
    email = db.Column(db.String(200))
    telefone = db.Column(db.String(50))
    gabinete = db.Column(db.String(50))
    endereco = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'partido': self.partido,
            'uf': self.uf,
            'cargo': self.cargo,
            'email': self.email,
            'telefone': self.telefone,
            'gabinete': self.gabinete,
            'endereco': self.endereco
        }

class EmailHistory(db.Model):
    __tablename__ = 'email_history'
    
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(500), nullable=False)
    message = db.Column(db.Text, nullable=False)
    sender_name = db.Column(db.String(200), nullable=False)
    sender_email = db.Column(db.String(200), nullable=False)
    recipients_count = db.Column(db.Integer, nullable=False)
    sent = db.Column(db.Integer, default=0)
    failed = db.Column(db.Integer, default=0)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'subject': self.subject,
            'message': self.message,
            'sender_name': self.sender_name,
            'sender_email': self.sender_email,
            'recipients_count': self.recipients_count,
            'sent': self.sent,
            'failed': self.failed,
            'date': self.date.isoformat()
        }

