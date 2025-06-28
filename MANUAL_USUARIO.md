# Sistema de Contato com Parlamentares

## Visão Geral

O Sistema de Contato com Parlamentares é uma aplicação web desenvolvida em Python que permite aos cidadãos enviar e-mails personalizados em massa para deputados e senadores brasileiros. A aplicação facilita o engajamento cívico ao automatizar o processo de comunicação com representantes políticos.

## Características Principais

### ✅ Funcionalidades Implementadas

- **Upload de Planilhas**: Suporte para arquivos .xls, .xlsx e .csv
- **Detecção Automática**: Reconhece automaticamente planilhas da Câmara dos Deputados e Senado Federal
- **Sistema de Filtros**: Filtragem por nome, partido, estado e cargo
- **Seleção Flexível**: Checkboxes individuais com opções de selecionar todos/limpar seleção
- **Personalização de E-mails**: Mensagens personalizadas com nome do parlamentar
- **Prévia de E-mail**: Visualização antes do envio
- **Envio em Massa**: Suporte para múltiplos provedores de e-mail (Gmail, Outlook, Yahoo, etc.)
- **Histórico Completo**: Registro de todos os envios realizados
- **Interface Responsiva**: Funciona em desktop, tablet e mobile
- **Banco de Dados**: Armazenamento persistente com SQLite

### 🌐 Compatibilidade

- **Sistemas Operacionais**: Windows, macOS, Linux, Android (via navegador)
- **Navegadores**: Chrome, Firefox, Safari, Edge
- **Provedores de E-mail**: Gmail, Outlook, Yahoo, UOL, Terra, IG e outros

## Requisitos do Sistema

### Requisitos Mínimos

- Python 3.8 ou superior
- 2 GB de RAM
- 500 MB de espaço em disco
- Conexão com a internet
- Navegador web moderno

### Dependências Python

```
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Flask-CORS==4.0.0
pandas==2.0.3
xlrd==2.0.1
openpyxl==3.1.2
```

## Instalação

### Passo 1: Preparar o Ambiente

```bash
# Clonar ou baixar os arquivos da aplicação
cd parlamentares_app

# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
# No Windows:
venv\Scripts\activate
# No Linux/Mac:
source venv/bin/activate
```

### Passo 2: Instalar Dependências

```bash
pip install -r requirements.txt
```

### Passo 3: Executar a Aplicação

```bash
python src/main.py
```

A aplicação estará disponível em: `http://localhost:5000`

## Configuração de E-mail

### Gmail

1. Ative a verificação em duas etapas na sua conta Google
2. Gere uma senha de aplicativo:
   - Acesse: https://myaccount.google.com/apppasswords
   - Selecione "E-mail" e "Computador Windows/Mac/Linux"
   - Use a senha gerada na aplicação

### Outlook/Hotmail

1. Acesse as configurações de segurança da conta Microsoft
2. Ative a verificação em duas etapas
3. Gere uma senha de aplicativo para uso na aplicação

### Outros Provedores

A aplicação suporta automaticamente os principais provedores brasileiros:
- UOL, Terra, IG, Yahoo Brasil

## Como Usar

### 1. Importar Dados dos Parlamentares

1. **Obter Planilhas Oficiais**:
   - Câmara dos Deputados: https://www.camara.leg.br/internet/deputado/deputado.xls
   - Senado Federal: Dados disponíveis em https://www12.senado.leg.br/dados-abertos

2. **Upload na Aplicação**:
   - Clique na área de upload ou arraste o arquivo
   - A aplicação detecta automaticamente o formato
   - Aguarde o processamento dos dados

### 2. Filtrar Parlamentares

1. **Filtros Disponíveis**:
   - **Nome**: Digite parte do nome do parlamentar
   - **Partido**: Selecione um partido específico
   - **Estado**: Escolha um estado (UF)
   - **Cargo**: Deputado ou Senador

2. **Aplicar Filtros**:
   - Configure os filtros desejados
   - Clique em "Aplicar Filtros"
   - Use "Limpar Filtros" para resetar

### 3. Selecionar Destinatários

1. **Seleção Individual**: Marque os checkboxes dos parlamentares desejados
2. **Seleção em Massa**: Use "Selecionar Todos" ou "Limpar Seleção"
3. **Verificação**: O contador mostra quantos estão selecionados

### 4. Compor Mensagem

1. **Campos Obrigatórios**:
   - **Assunto**: Título do e-mail
   - **Mensagem**: Corpo do e-mail (use `{nome}` para personalizar)
   - **Seu Nome**: Nome do remetente
   - **Seu E-mail**: E-mail de origem
   - **Senha**: Senha do e-mail ou senha de aplicativo

2. **Personalização**:
   - Use `{nome}` na mensagem para incluir o nome do parlamentar
   - Exemplo: "Prezado(a) {nome}, solicito seu apoio..."

### 5. Enviar E-mails

1. **Prévia**: Clique em "Visualizar E-mail" para ver como ficará
2. **Envio**: Clique em "Enviar E-mails" para iniciar o processo
3. **Acompanhamento**: Veja o progresso e resultados na tela

### 6. Consultar Histórico

- Todos os envios são registrados automaticamente
- Visualize data, assunto, quantidade e status dos envios
- Use "Atualizar Histórico" para ver os dados mais recentes

## Estrutura de Arquivos

```
parlamentares_app/
├── src/
│   ├── main.py                 # Arquivo principal da aplicação
│   ├── models/
│   │   └── parlamentar.py      # Modelos de dados
│   ├── routes/
│   │   └── parlamentar.py      # Rotas da API
│   ├── static/
│   │   └── index.html          # Interface web
│   └── database/
│       └── app.db              # Banco de dados SQLite
├── venv/                       # Ambiente virtual
├── requirements.txt            # Dependências
└── README.md                   # Documentação
```

## Segurança e Privacidade

### Dados Pessoais

- A aplicação não armazena senhas de e-mail
- Dados dos parlamentares são públicos e oficiais
- Histórico de envios fica apenas no computador local

### Recomendações de Segurança

1. **Use senhas de aplicativo** em vez da senha principal
2. **Mantenha o software atualizado**
3. **Não compartilhe suas credenciais**
4. **Execute apenas em computadores confiáveis**

## Solução de Problemas

### Erro de Autenticação de E-mail

**Problema**: "Erro na autenticação do e-mail"

**Soluções**:
1. Verifique se a senha está correta
2. Use senha de aplicativo (Gmail/Outlook)
3. Ative a verificação em duas etapas
4. Verifique se o provedor está suportado

### Planilha Não Reconhecida

**Problema**: "Erro ao processar arquivo"

**Soluções**:
1. Verifique se o arquivo não está corrompido
2. Certifique-se de que é uma planilha oficial
3. Tente converter para .csv se necessário
4. Verifique se o arquivo não está muito grande

### Interface Não Carrega

**Problema**: Página em branco ou erro 500

**Soluções**:
1. Verifique se todas as dependências estão instaladas
2. Confirme se o Python está na versão correta
3. Reinicie a aplicação
4. Verifique os logs no terminal

### Filtros Não Funcionam

**Problema**: Filtros não mostram resultados

**Soluções**:
1. Certifique-se de que os dados foram carregados
2. Verifique se há parlamentares com os critérios selecionados
3. Use "Limpar Filtros" e tente novamente
4. Recarregue a página se necessário

## Limitações Conhecidas

1. **Volume de E-mails**: Provedores podem limitar envios em massa
2. **Velocidade**: Envio sequencial para evitar bloqueios
3. **Formatos**: Suporte limitado a planilhas muito antigas
4. **Conectividade**: Requer conexão estável com a internet

## Suporte Técnico

### Logs e Depuração

Para obter informações detalhadas sobre erros:

1. Execute a aplicação no terminal
2. Observe as mensagens de erro
3. Verifique o arquivo de log (se disponível)
4. Anote a mensagem de erro exata

### Informações para Suporte

Ao solicitar ajuda, inclua:

- Sistema operacional e versão
- Versão do Python
- Mensagem de erro completa
- Passos que levaram ao problema
- Tipo de arquivo sendo usado

## Atualizações e Melhorias Futuras

### Funcionalidades Planejadas

- [ ] Agendamento de envios
- [ ] Templates de mensagens
- [ ] Relatórios detalhados
- [ ] Integração com redes sociais
- [ ] Modo offline para composição
- [ ] Backup automático de dados

### Como Contribuir

1. Reporte bugs encontrados
2. Sugira melhorias
3. Teste com diferentes tipos de planilhas
4. Compartilhe feedback sobre usabilidade

## Licença e Termos de Uso

### Uso Responsável

Esta aplicação foi desenvolvida para facilitar a comunicação legítima entre cidadãos e seus representantes eleitos. Use de forma responsável:

1. **Não envie spam** ou mensagens irrelevantes
2. **Seja respeitoso** na comunicação
3. **Use dados públicos** apenas
4. **Respeite limites** dos provedores de e-mail
5. **Mantenha o tom civilizado** nas mensagens

### Isenção de Responsabilidade

- O desenvolvedor não se responsabiliza pelo uso inadequado da ferramenta
- Usuários são responsáveis pelo conteúdo das mensagens enviadas
- A aplicação é fornecida "como está", sem garantias
- Use por sua própria conta e risco

## Conclusão

O Sistema de Contato com Parlamentares é uma ferramenta poderosa para o exercício da cidadania digital. Ao facilitar a comunicação com representantes políticos, contribui para uma democracia mais participativa e transparente.

Para dúvidas, sugestões ou problemas, consulte esta documentação ou entre em contato através dos canais de suporte disponíveis.

---

**Versão da Documentação**: 1.0  
**Data**: Junho de 2025  
**Compatibilidade**: Python 3.8+, Flask 2.3+

