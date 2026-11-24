from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import httpx

app = FastAPI(title="API Gateway - HelpDesk TI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

USERS_URL = "http://ms-users:8001"
ASSETS_URL = "http://ms-assets:8002"
TICKETS_URL = "http://ms-tickets:8003"
ROTAS = {
    "/auth": USERS_URL,
    "/usuarios": USERS_URL,
    "/ativos": ASSETS_URL,
    "/chamados": TICKETS_URL,
    "/notificacoes": TICKETS_URL,
}

app.mount("/static", StaticFiles(directory="web"), name="static")

@app.get("/")
async def root():
    return FileResponse("web/index.html")

@app.get("/estilo.css")
async def serve_css():
    return FileResponse("web/estilo.css")

@app.get("/app.js")
async def serve_js():
    return FileResponse("web/app.js")

@app.get("/saude")
async def health_check():
    status = {}
    async with httpx.AsyncClient(timeout=2.0) as client:
        for nome, url in [("users", USERS_URL), ("assets", ASSETS_URL), ("tickets", TICKETS_URL)]:
            try:
                r = await client.get(f"{url}/saude")
                status[nome] = "ok" if r.status_code == 200 else "erro"
            except:
                status[nome] = "offline"
    return status

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy(path: str, request: Request):
    destino = None
    for prefixo, url in ROTAS.items():
        if f"/{path}".startswith(prefixo):
            destino = url
            break

    if not destino:
        return Response(status_code=404, content="Rota não encontrada no Gateway.")

    url_final = f"{destino}/{path}"
    headers = dict(request.headers)
    headers.pop("host", None)
    body = await request.body()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resposta = await client.request(
                method=request.method,
                url=url_final,
                headers=headers,
                content=body,
                params=request.query_params,
            )
            return Response(
                content=resposta.content,
                status_code=resposta.status_code,
                headers=dict(resposta.headers),
            )
    except httpx.RequestError:
        return Response(status_code=503, content="Serviço indisponível.")