"""Regras do módulo de chamados.

Repare nas chamadas para `usuarios.servico`, `inventario.servico` e
`notificacoes.servico`: no monólito elas são chamadas de função, dentro do
mesmo processo. Em microsserviços, elas viram chamadas pela rede ou eventos.

Permissões:
- solicitante: abre chamados e só vê, comenta e fecha os próprios;
- técnico e admin: veem todos, atribuem e mudam o status.
"""
import json
from collections import Counter
from datetime import datetime, timedelta

import httpx
import redis
from sqlalchemy.orm import Session

from chamados import repositorio
from chamados.esquemas import ChamadoCriar, ComentarioCriar
from chamados.modelos import Chamado, Comentario
from erros import NaoEncontrado, RegraDeNegocio, SemPermissao
from config import USUARIOS_URL, INVENTARIO_URL, REDIS_URL

# Prazo para resolver o chamado, conforme a prioridade (SLA)
HORAS_SLA = {"critica": 4, "alta": 8, "media": 24, "baixa": 72}

# De qual status para quais status um chamado pode ir
TRANSICOES = {
    "aberto": {"em_atendimento"},
    "em_atendimento": {"resolvido"},
    "resolvido": {"fechado", "em_atendimento"},  # reabrir se o problema voltar
    "fechado": set(),
}

EQUIPE = ("tecnico", "admin")

# Conexão com o Redis para publicar eventos
redis_client = redis.from_url(REDIS_URL)


class UsuarioToken:
    """Representa o usuário extraído do token (sem consultar o banco de usuários)."""
    def __init__(self, id: int, perfil: str):
        self.id = id
        self.perfil = perfil
        self.ativo = True


def eh_equipe(usuario: UsuarioToken) -> bool:
    return usuario.perfil in EQUIPE


def calcular_prazo(prioridade: str, inicio: datetime) -> datetime:
    return inicio + timedelta(hours=HORAS_SLA[prioridade])


def publicar_evento(tipo: str, usuario_id: int, mensagem: str):
    """Publica um evento no canal do Redis para o ms-notificacoes consumir."""
    try:
        evento = {
            "tipo": tipo,
            "usuario_id": usuario_id,
            "mensagem": mensagem,
        }
        redis_client.publish("canal_chamados", json.dumps(evento))
        print(f"📤 Evento publicado: {tipo} para usuário {usuario_id}")
    except Exception as e:
        # Não falha a operação principal se o Redis estiver fora
        print(f"❌ Erro ao publicar evento: {e}")


def verificar_ativo(ativo_id: int, token: str) -> dict:
    """Chama o ms-inventario via HTTP para validar o ativo."""
    try:
        resposta = httpx.get(
            f"{INVENTARIO_URL}/ativos/{ativo_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5.0,
        )
        resposta.raise_for_status()
        return resposta.json()
    except httpx.HTTPStatusError:
        raise RegraDeNegocio(f"Ativo {ativo_id} não encontrado.")
    except httpx.RequestError:
        raise RegraDeNegocio("Serviço de inventário indisponível.")


def verificar_tecnico(tecnico_id: int, token: str) -> dict:
    """Chama o ms-usuarios via HTTP para validar o técnico."""
    try:
        resposta = httpx.get(
            f"{USUARIOS_URL}/usuarios/{tecnico_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5.0,
        )
        resposta.raise_for_status()
        dados = resposta.json()
        if dados.get("perfil") != "tecnico":
            raise RegraDeNegocio(f"Usuário {tecnico_id} não é técnico.")
        return dados
    except httpx.HTTPStatusError:
        raise RegraDeNegocio(f"Usuário {tecnico_id} não encontrado.")
    except httpx.RequestError:
        raise RegraDeNegocio("Serviço de usuários indisponível.")


def abrir(db: Session, dados: ChamadoCriar, usuario: UsuarioToken, token: str) -> Chamado:
    if dados.ativo_id is not None:
        verificar_ativo(dados.ativo_id, token)  # vira chamada HTTP

    agora = datetime.now()
    chamado = repositorio.salvar(db, Chamado(
        **dados.model_dump(), solicitante_id=usuario.id, status="aberto", criado_em=agora,
        prazo_sla=calcular_prazo(dados.prioridade, agora),
    ))

    # Publica o evento ChamadoAberto
    publicar_evento(
        "ChamadoAberto",
        usuario.id,
        f"Seu chamado #{chamado.id} foi aberto. Prazo: {chamado.prazo_sla:%d/%m %H:%M}."
    )
    return chamado


def obter(db: Session, chamado_id: int, usuario: UsuarioToken) -> Chamado:
    chamado = repositorio.buscar_por_id(db, chamado_id)
    # Para quem não pode ver, responde "não encontrado": não revela que o chamado existe
    if chamado is None or not (eh_equipe(usuario) or chamado.solicitante_id == usuario.id):
        raise NaoEncontrado(f"Chamado {chamado_id} não encontrado.")
    return chamado


def listar(db: Session, usuario: UsuarioToken, status: str | None = None, tecnico_id: int | None = None) -> list[Chamado]:
    solicitante_id = None if eh_equipe(usuario) else usuario.id
    return repositorio.listar(db, status, tecnico_id, solicitante_id)


def atribuir(db: Session, chamado_id: int, tecnico_id: int, usuario: UsuarioToken, token: str) -> Chamado:
    if not eh_equipe(usuario):
        raise SemPermissao("Só técnicos e administradores atribuem chamados.")
    chamado = obter(db, chamado_id, usuario)
    if chamado.status in ("resolvido", "fechado"):
        raise RegraDeNegocio("Não é possível atribuir um chamado resolvido ou fechado.")
    tecnico = verificar_tecnico(tecnico_id, token)  # vira chamada HTTP
    chamado.tecnico_id = tecnico["id"]
    if chamado.status == "aberto":
        chamado.status = "em_atendimento"
    repositorio.salvar(db, chamado)

    # Publica o evento ChamadoAtribuido
    publicar_evento(
        "ChamadoAtribuido",
        tecnico["id"],
        f"O chamado #{chamado.id} foi atribuído a você."
    )
    return chamado


def mudar_status(db: Session, chamado_id: int, novo_status: str, usuario: UsuarioToken) -> Chamado:
    chamado = obter(db, chamado_id, usuario)
    # O solicitante só pode confirmar (fechar) ou reabrir o próprio chamado resolvido
    pode_solicitante = chamado.status == "resolvido" and novo_status in ("fechado", "em_atendimento")
    if not (eh_equipe(usuario) or pode_solicitante):
        raise SemPermissao("Você não pode mudar o status deste chamado.")
    if novo_status not in TRANSICOES[chamado.status]:
        raise RegraDeNegocio(f"Não é possível ir de '{chamado.status}' para '{novo_status}'.")
    if novo_status == "em_atendimento" and chamado.tecnico_id is None:
        raise RegraDeNegocio("Atribua um técnico antes de iniciar o atendimento.")
    chamado.status = novo_status
    repositorio.salvar(db, chamado)

    # Publica o evento ChamadoResolvido (apenas quando o status for "resolvido")
    if novo_status == "resolvido":
        publicar_evento(
            "ChamadoResolvido",
            chamado.solicitante_id,
            f"Seu chamado #{chamado.id} foi resolvido. Confirme se está tudo certo."
        )
    return chamado


def comentar(db: Session, chamado_id: int, dados: ComentarioCriar, usuario: UsuarioToken) -> Comentario:
    chamado = obter(db, chamado_id, usuario)
    if chamado.status == "fechado":
        raise RegraDeNegocio("Chamados fechados não recebem comentários.")
    return repositorio.salvar_comentario(db, Comentario(
        chamado_id=chamado.id, autor_id=usuario.id, texto=dados.texto, criado_em=datetime.now()
    ))


def painel(db: Session, usuario: UsuarioToken) -> dict:
    chamados = listar(db, usuario)
    agora = datetime.now()
    atrasados = sum(1 for c in chamados if c.status in ("aberto", "em_atendimento") and c.prazo_sla < agora)
    return {"total": len(chamados), "por_status": dict(Counter(c.status for c in chamados)), "atrasados": atrasados}