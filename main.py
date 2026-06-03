from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, Response
from dotenv import load_dotenv

from database import init_db, insertar_nota

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def health_check() -> dict[str, str]:
    return {"status": "activo"}


@app.post("/webhook")
async def webhook(request: Request) -> Response:
    payload: dict[str, Any] = await request.json()

    texto = (
        payload.get("Body")
        or payload.get("text")
        or payload.get("mensaje")
        or str(payload)
    )

    nota_id = await insertar_nota(texto)
    print(f"[webhook] Nota #{nota_id} guardada: {texto[:80]}")

    return Response(status_code=200)
