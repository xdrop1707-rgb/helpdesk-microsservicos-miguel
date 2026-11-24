from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from usuarios.rotas import router as usuarios_router
from auth.rotas import router as auth_router
from database import Base, engine, SessionLocal
from config import DADOS_EXEMPLO
from seguranca_http import CabecalhosDeSeguranca
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ms-usuarios")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Microsserviço de Usuários e Auth")

app.add_middleware(CabecalhosDeSeguranca)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(usuarios_router)

@app.get("/saude")
def health_check():
    return {"status": "ok", "servico": "usuarios"}

@app.on_event("startup")
def popular_banco():
    if not DADOS_EXEMPLO:
        return
    
    from dados_exemplo import carregar
    db = SessionLocal()
    try:
        log.info("Verificando dados de exemplo...")
        carregar(db)
        log.info("Dados de exemplo verificados/criados com sucesso.")
    except Exception as e:
        log.error(f"Erro ao criar dados de exemplo: {e}")
    finally:
        db.close()