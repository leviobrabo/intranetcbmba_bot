# Intranet CBMBA

## Bot CBMBA Intranet Scraper

Este é um bot projetado para acessar a intranet do CBMBA via web scraping, coletar os avisos disponíveis e enviá-los para um canal específico do Telegram.

## Funcionalidades

- Realiza login na intranet do CBMBA (autenticação com credenciais).
- Coleta os avisos ou informações relevantes disponíveis.
- Formata os dados coletados para leitura e envio.
- Envia os avisos diretamente para um canal ou grupo do Telegram.

## Requisitos

### Tecnologias utilizadas
- **Python**: Linguagem principal do bot.
- **Bibliotecas**:
  - `requests`: Para realizar conexões HTTP.
  - `BeautifulSoup`: Para parsing e scraping de conteúdo HTML.
  - `python-telegram-bot`: Para integração com o Telegram.
  - `dotenv`: Para gerenciar variáveis de ambiente.
  - `schedule` (opcional): Para agendar execuções periódicas.

### Configurações necessárias
1. **Credenciais da Intranet:**
   - Usuário e senha para acessar a intranet do CBMBA.
   - Configure essas informações no arquivo `.env`.

2. **Token do Bot do Telegram:**
   - Crie um bot no Telegram via BotFather e obtenha o token.
   - Configure o token no arquivo `.env`.

3. **ID do Canal/Grupo do Telegram:**
   - Obtenha o ID do canal ou grupo para onde os avisos devem ser enviados.
   - Configure no arquivo `.env`.

## Configuração do Ambiente

### 1. Clonar o repositório
```bash
git clone https://github.com/seu-usuario/intranetcbmba_bot.git
cd intranetcbmba_bot
```

### 2. Criar e ativar um ambiente virtual
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows
```

### 3. Instalar dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar o arquivo `.env`
Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:
```env
[DEFAULT]
LOGIN_URL = http://www.cbm.ba.gov.br/user/login
AVISOS_URL = http://www.cbm.ba.gov.br/acesso-restrito/listar-avisos
BASE_URL = http://www.cbm.ba.gov.br
CHECK_INTERVAL = 60

[USER]
USERNAME = 
PASSWORD = 

[TELEGRAM]
TELEGRAM_TOKEN = 
CHAT_ID = 

[MONGODB]
MONGO_URI = 
MONGO_DB = cbm_bot_db
MONGO_COLLECTION = avisos_enviados

```

### 5. Executar o bot
```bash
python bot.py
```

## Estrutura do Projeto
```
cbmba-bot/
├── main.py               # Script principal do bot
├── bot.conf             # Configurações sensíveis
└── requirements.txt     # Dependências do projeto
```

## Automação (opcional)
Para executar o bot periodicamente:

## Contribuições
Contribuições são bem-vindas! Para relatar problemas ou sugerir melhorias, abra uma issue ou envie um pull request.

## Licença
Este projeto está licenciado sob a MIT License. Consulte o arquivo `LICENSE` para mais informações.
