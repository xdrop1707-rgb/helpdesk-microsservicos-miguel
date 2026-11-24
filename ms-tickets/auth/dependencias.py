"""Dependências do FastAPI para exigir login e perfil (baseado apenas no token JWT)."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth import tokens

esquema = HTTPBearer(auto_error=False)

NAO_AUTENTICADO = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Faça login para continuar.",
    headers={"WWW-Authenticate": "Bearer"},
)

class UsuarioToken:
    def __init__(self, id: int, perfil: str):
        self.id = id
        self.perfil = perfil
        self.ativo = True

def usuario_atual(
    credenciais: HTTPAuthorizationCredentials | None = Depends(esquema),
) -> UsuarioToken:
    if credenciais is None or credenciais.scheme.lower() != "bearer":
        raise NAO_AUTENTICADO
    try:
        dados_token = tokens.ler_completo(credenciais.credentials)
        return UsuarioToken(id=dados_token["id"], perfil=dados_token["perfil"])
    except tokens.TokenInvalido:
        raise NAO_AUTENTICADO

def exigir_perfil(*perfis: str):
    def verificar(usuario: UsuarioToken = Depends(usuario_atual)) -> UsuarioToken:
        if usuario.perfil not in perfis:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não tem permissão para esta ação.")
        return usuario
    return verificar