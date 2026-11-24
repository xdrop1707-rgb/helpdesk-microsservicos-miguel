import logging
import os
import secrets

log = logging.getLogger("helpdesk")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:senha123@localhost:5433/usuarios_db")

# Lê o segredo do ambiente. Se não existir, usa o padrão (sem gerar aleatório!)
JWT_SEGREDO = os.getenv("JWT_SEGREDO", "super_segredo_usuarios")
if not JWT_SEGREDO:
    log.warning("JWT_SEGREDO não definido; usando um segredo aleatório.")
    JWT_SEGREDO = secrets.token_urlsafe(48)

JWT_ALGORITMO = "HS256"
JWT_EMISSOR = "helpdesk-ti"
TOKEN_MINUTOS = int(os.getenv("TOKEN_MINUTOS", "60"))
LOGIN_MAX_FALHAS = int(os.getenv("LOGIN_MAX_FALHAS", "5"))
LOGIN_JANELA_SEGUNDOS = int(os.getenv("LOGIN_JANELA_SEGUNDOS", "300"))
TAMANHO_MAXIMO_REQUISICAO = 64 * 1024
DOCS_ATIVA = os.getenv("DOCS", "1") == "1"
DADOS_EXEMPLO = os.getenv("DADOS_EXEMPLO", "1") == "1"
SENHA_EXEMPLO = os.getenv("SENHA_EXEMPLO", "Helpdesk2026")