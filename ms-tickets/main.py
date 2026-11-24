from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from chamados.rotas import router as chamados_router
from database import Base, engine
from seguranca_http import CabecalhosDeSeguranca
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ms-chamados")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Microsserviço de Chamados")

app.add_middleware(CabecalhosDeSeguranca)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chamados_router)

@app.get("/saude")
def health_check():
    return {"status": "ok", "servico": "chamados"}