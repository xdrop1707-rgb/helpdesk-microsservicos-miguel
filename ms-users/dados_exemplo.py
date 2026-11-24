"""Cria dados de exemplo de USUÁRIOS quando o banco está vazio.

Uso apenas em aula: todos os usuários de exemplo têm a mesma senha
(variável SENHA_EXEMPLO). Em produção, rode com DADOS_EXEMPLO=0.
"""
import os
from sqlalchemy.orm import Session

from usuarios import servico as usuarios
from usuarios.esquemas import UsuarioCriar

SENHA = os.getenv("SENHA_EXEMPLO", "Helpdesk2026")


def carregar(db: Session) -> None:
    if usuarios.listar(db):
        return
    
    novo = lambda nome, email, perfil: usuarios.criar(db, UsuarioCriar(nome=nome, email=email, perfil=perfil, senha=SENHA))
    
    # Cria apenas os usuários
    novo("Admin TI", "admin@empresa.com", "admin")
    novo("Ana Souza", "ana@empresa.com", "solicitante")
    novo("Bruno Lima", "bruno@empresa.com", "solicitante")
    novo("Carla Dias", "carla@empresa.com", "tecnico")
    novo("Diego Rocha", "diego@empresa.com", "tecnico")