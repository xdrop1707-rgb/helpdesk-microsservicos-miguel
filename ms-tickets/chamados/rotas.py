from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from auth.dependencias import usuario_atual, UsuarioToken
from chamados import servico
from chamados.esquemas import (
    Atribuicao, ChamadoCriar, ChamadoSaida, ComentarioCriar, ComentarioSaida, MudancaStatus, Painel, Status,
)
from database import get_db

router = APIRouter(prefix="/chamados", tags=["Chamados"])


@router.post("", response_model=ChamadoSaida, status_code=201)
def abrir_chamado(dados: ChamadoCriar, request: Request, usuario: UsuarioToken = Depends(usuario_atual), db: Session = Depends(get_db)):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    return servico.abrir(db, dados, usuario, token)


@router.get("", response_model=list[ChamadoSaida])
def listar_chamados(status: Status | None = None, tecnico_id: int | None = None,
                    usuario: UsuarioToken = Depends(usuario_atual), db: Session = Depends(get_db)):
    return servico.listar(db, usuario, status, tecnico_id)


@router.get("/painel", response_model=Painel)
def painel(usuario: UsuarioToken = Depends(usuario_atual), db: Session = Depends(get_db)):
    return servico.painel(db, usuario)


@router.get("/{chamado_id}", response_model=ChamadoSaida)
def obter_chamado(chamado_id: int, usuario: UsuarioToken = Depends(usuario_atual), db: Session = Depends(get_db)):
    return servico.obter(db, chamado_id, usuario)


@router.patch("/{chamado_id}/atribuir", response_model=ChamadoSaida)
def atribuir_chamado(chamado_id: int, dados: Atribuicao, request: Request, usuario: UsuarioToken = Depends(usuario_atual), db: Session = Depends(get_db)):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    return servico.atribuir(db, chamado_id, dados.tecnico_id, usuario, token)


@router.patch("/{chamado_id}/status", response_model=ChamadoSaida)
def mudar_status(chamado_id: int, dados: MudancaStatus, usuario: UsuarioToken = Depends(usuario_atual), db: Session = Depends(get_db)):
    return servico.mudar_status(db, chamado_id, dados.status, usuario)


@router.post("/{chamado_id}/comentarios", response_model=ComentarioSaida, status_code=201)
def comentar(chamado_id: int, dados: ComentarioCriar, usuario: UsuarioToken = Depends(usuario_atual), db: Session = Depends(get_db)):
    return servico.comentar(db, chamado_id, dados, usuario)