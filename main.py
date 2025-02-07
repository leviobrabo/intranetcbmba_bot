import os
import requests
from bs4 import BeautifulSoup
import telebot
import time
import schedule
import logging
from typing import List, Dict
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Carregar configurações do arquivo .env
LOGIN_URL = os.getenv('LOGIN_URL')
AVISOS_URL = os.getenv('AVISOS_URL')
BASE_URL = os.getenv('BASE_URL')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 60))

USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB = os.getenv('MONGO_DB')
MONGO_COLLECTION = os.getenv('MONGO_COLLECTION')

DOCUMENTS_DIR = "documentos"
if not os.path.exists(DOCUMENTS_DIR):
    os.makedirs(DOCUMENTS_DIR)

# Configuração de Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler() 
    ]
)

# Inicializa o bot do Telegram usando pytelegrambotapi
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Inicia uma sessão
session = requests.Session()

# Define um User-Agent para evitar bloqueios de requisições automatizadas
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
})

# Configura o MongoDB
client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
collection = db[MONGO_COLLECTION]

# Cria o diretório para documentos se não existir
if not os.path.exists(DOCUMENTS_DIR):
    os.makedirs(DOCUMENTS_DIR)

def login() -> bool:
    """
    Realiza login no site e mantém a sessão autenticada.
    """
    logging.info("Tentando realizar login...")
    try:
        response = session.get(LOGIN_URL)
        print(response.status_code)
        print(response.text)
        logging.info(f"Resposta GET LOGIN_URL: {response.status_code}")
        soup = BeautifulSoup(response.text, 'html.parser')

        form_build_id = soup.find('input', {'name': 'form_build_id'})
        form_id = soup.find('input', {'name': 'form_id'})

        if not form_build_id or not form_id:
            logging.error("Campos do formulário de login não encontrados. Verifique a página de login.")
            return False

        payload = {
            'name': USERNAME,
            'pass': PASSWORD,
            'form_build_id': form_build_id['value'],
            'form_id': form_id['value'],
            'op': 'Entrar'
        }

        logging.info(f"Payload de login: {payload}")
        login_response = session.post(LOGIN_URL, data=payload)
        logging.info(f"Resposta POST LOGIN_URL: {login_response.status_code}")

        if "Sair" in login_response.text:
            logging.info("Login realizado com sucesso.")
            return True
        else:
            logging.error("Falha no login. Verifique suas credenciais.")
            return False
    except Exception as e:
        logging.error(f"Erro durante o login: {e}")
        return False


def extrair_avisos() -> List[Dict]:
    """
    Extrai a lista de avisos da página de avisos do dia.
    Retorna uma lista de dicionários com data_hora, titulo e link.
    """
    try:
        response = session.get(AVISOS_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        avisos = []
        tabela = soup.find('tbody')
        if not tabela:
            logging.warning("Tabela de avisos não encontrada.")
            return avisos

        linhas = tabela.find_all('tr')

        hoje = datetime.now().strftime("%d/%m/%Y")

        for linha in linhas:
            data_hora = linha.find('td', class_='views-field-created').get_text(strip=True)
            titulo_tag = linha.find('td', class_='views-field-title').find('a')
            if not titulo_tag:
                continue
            titulo = titulo_tag.get_text(strip=True)
            link = BASE_URL + titulo_tag['href']
            aviso_id = titulo_tag['href'].split('/')[-1]  # Extração do ID do aviso

            # Filtra apenas os avisos do dia
            if data_hora.startswith(hoje):
                avisos.append({
                    'id': aviso_id,
                    'data_hora': data_hora,
                    'titulo': titulo,
                    'link': link
                })

        logging.info(f"{len(avisos)} avisos do dia extraídos.")
        return avisos
    except Exception as e:
        logging.error(f"Erro ao extrair avisos: {e}")
        return []

def extrair_documentos(link_aviso: str) -> List[Dict]:
    """
    Extrai documentos anexados a um aviso específico.
    Retorna uma lista de dicionários com nome e URL do documento.
    """
    try:
        response = session.get(link_aviso)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        documentos = []
        documentos_section = soup.find('div', class_='field--name-field-documentos')
        if documentos_section:
            arquivos = documentos_section.find_all('a', href=True)
            for arquivo in arquivos:
                url_arquivo = arquivo['href']
                nome_arquivo = arquivo.get_text(strip=True)
                documentos.append({
                    'nome': nome_arquivo,
                    'url': url_arquivo
                })
        return documentos
    except Exception as e:
        logging.error(f"Erro ao extrair documentos do aviso {link_aviso}: {e}")
        return []

def baixar_documentos(documentos: List[Dict]) -> List[str]:
    """
    Baixa os documentos e retorna uma lista com os caminhos dos arquivos locais.
    """
    caminhos = []
    try:
        for doc in documentos:
            url = doc['url']
            nome = doc['nome']
            resposta = session.get(url, stream=True)
            resposta.raise_for_status()

            caminho_arquivo = os.path.join(DOCUMENTS_DIR, nome)
            with open(caminho_arquivo, 'wb') as f:
                for chunk in resposta.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            caminhos.append(caminho_arquivo)
            logging.info(f"Documento baixado: {nome}")
        return caminhos
    except Exception as e:
        logging.error(f"Erro ao baixar documentos: {e}")
        return []
        
def enviar_documentos_por_lotes(documentos: List[Dict]):
    """
    Envia documentos em lotes de 10 por vez para evitar o erro do Telegram.
    """
    try:
        # Dividir os documentos em lotes de 10
        for i in range(0, len(documentos), 10):
            lote = documentos[i:i+10]
            arquivos = [doc['url'] for doc in lote]

            # Enviar lote de documentos como um álbum
            bot.send_media_group(
                chat_id=CHAT_ID,
                media=[telebot.types.InputMediaDocument(url=arquivo) for arquivo in arquivos]
            )
            logging.info(f"Enviado lote de {len(lote)} documentos.")
    except Exception as e:
        logging.error(f"Erro ao enviar documentos para o Telegram: {e}")
        
def extrair_conteudo_aviso(link_aviso: str) -> str:
    """
    Extrai o conteúdo completo do aviso a partir do link.
    Retorna o texto do aviso com espaçamento entre parágrafos e quebra de linha onde necessário.
    """
    try:
        response = session.get(link_aviso)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        conteudo_section = soup.find('div', class_='field--name-body')
        if conteudo_section:
            # Remove scripts, estilos e outros elementos indesejados
            for script in conteudo_section(["script", "style"]):
                script.decompose()
            # Extrai o texto e adiciona espaçamento entre parágrafos
            texto = "\n\n".join(
                p.get_text(strip=True) for p in conteudo_section.find_all('p') if p.get_text(strip=True)
            )
            # Adiciona quebra de linha onde não há espaço claro
            texto_formatado = texto.replace(" - CEL BM", " - CEL BM\n")
            return texto_formatado
        else:
            logging.warning(f"Conteúdo do aviso {link_aviso} não encontrado.")
            return "Conteúdo não disponível."
    except Exception as e:
        logging.error(f"Erro ao extrair conteúdo do aviso {link_aviso}: {e}")
        return "Erro ao extrair conteúdo."

def enviar_para_telegram(aviso: Dict):
    """
    Envia o texto do aviso como uma mensagem individual e os documentos como uma mensagem agrupada.
    """
    try:
        # Extrai o conteúdo completo do aviso
        conteudo = extrair_conteudo_aviso(aviso['link'])

        # Extrai documentos
        documentos = extrair_documentos(aviso['link'])
    
        # Prepara a mensagem com o conteúdo do aviso com formatação HTML
        mensagem = (
            f"<b>{aviso['titulo']}</b>\n"
            f"<b>Data/Hora:</b> <code>{aviso['data_hora']}</code>\n\n"
            f"<blockquote>{conteudo}</blockquote>"
        )

        # Envia a mensagem com o conteúdo do aviso
        bot.send_message(chat_id=CHAT_ID, text=mensagem, parse_mode='HTML')
        logging.info(f"Texto enviado para o aviso: {aviso['titulo']}")
        
        # Adiciona o ID do aviso ao MongoDB para evitar reenvios
        collection.insert_one({'id': aviso['id']})
        
        # Se houver documentos, envia-os como uma mensagem agrupada
        documentos = extrair_documentos(aviso['link'])
        if documentos:
            open_files = []  # Lista para manter os arquivos abertos
    
            for doc in documentos:
                url = doc['url']
                nome = doc['nome']
                resposta = session.get(url, stream=True)
                resposta.raise_for_status()
    
                # Salva o documento localmente
                caminho_arquivo = os.path.join(DOCUMENTS_DIR, nome)
                with open(caminho_arquivo, 'wb') as f:
                    for chunk in resposta.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
    
                # Abre o arquivo para envio
                f = open(caminho_arquivo, 'rb')
                open_files.append(f)  # Mantém o arquivo aberto
    
                # Envia o documento individualmente
                bot.send_document(chat_id=CHAT_ID, document=f)
                logging.info(f"Documento enviado para o aviso: {aviso['titulo']}")
    
                # Fecha e remove o arquivo após o envio
                f.close()
                os.remove(f.name)
    
            
            # Aguarda para evitar exceder os limites da API do Telegram
            time.sleep(1)
    except Exception as e:
        logging.error(f"Erro ao enviar aviso para o Telegram: {e}")

def limpar_dados():
    """
    Remove todos os documentos da coleção no MongoDB.
    """
    try:
        result = collection.delete_many({})
        logging.info(f"Dados do banco de dados limpos. {result.deleted_count} documento(s) removido(s).")
    except Exception as e:
        logging.error(f"Erro ao limpar dados do banco de dados: {e}")


def verificar_e_enviar():
    """
    Função principal que verifica por novos avisos do dia e os envia para o Telegram.
    """
    logging.info("Iniciando verificação de novos avisos do dia...")
    avisos = extrair_avisos()
    novos_avisos = [aviso for aviso in avisos if not collection.find_one({'id': aviso['id']})]

    if novos_avisos:
        logging.info(f"{len(novos_avisos)} novo(s) aviso(s) encontrado(s). Enviando para o Telegram...")
        for aviso in novos_avisos:
            enviar_para_telegram(aviso)
    else:
        logging.info("Nenhum novo aviso do dia encontrado.")

def main():
    """
    Função principal que realiza login e agenda a verificação periódica.
    """
    if not login():
        logging.critical("Não foi possível realizar o login. Encerrando o script.")
        return

    # Executa a primeira verificação imediatamente
    verificar_e_enviar()

    # Agenda a verificação a cada CHECK_INTERVAL segundos
    schedule.every(CHECK_INTERVAL).seconds.do(verificar_e_enviar)
    schedule.every().day.at("00:00").do(limpar_dados)
    logging.info(f"Bot iniciado. Verificações a cada {CHECK_INTERVAL} segundos.")

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
