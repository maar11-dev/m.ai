import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from dotenv import load_dotenv

from database import init_db, insertar_nota, obtener_notas, eliminar_nota

load_dotenv()

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def health_check() -> dict[str, str]:
    return {"status": "activo"}


@app.get("/notas")
async def listar_notas() -> list[dict]:
    return await obtener_notas()


@app.delete("/notas/{nota_id}", status_code=204)
async def borrar_nota(nota_id: int) -> Response:
    if not await eliminar_nota(nota_id):
        raise HTTPException(status_code=404, detail="Nota no encontrada")
    return Response(status_code=204)


@app.get("/webhook")
async def verificar_webhook(request: Request) -> Response:
    params = request.query_params
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return Response(content=params.get("hub.challenge", ""), media_type="text/plain")
    raise HTTPException(status_code=403, detail="Token inválido")


@app.post("/webhook")
async def webhook(request: Request) -> Response:
    payload: dict[str, Any] = await request.json()

    texto = (
        payload.get("entry", [{}])[0]
        .get("changes", [{}])[0]
        .get("value", {})
        .get("messages", [{}])[0]
        .get("text", {})
        .get("body")
        or payload.get("texto")
        or payload.get("Body")
        or payload.get("text")
        or payload.get("mensaje")
        or str(payload)
    )

    nota_id = await insertar_nota(texto)
    print(f"[webhook] Nota #{nota_id} guardada: {texto[:80]}")

    return Response(status_code=200)
