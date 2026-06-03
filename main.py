import os
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from dotenv import load_dotenv

from database import init_db, insertar_nota, obtener_notas, eliminar_nota

load_dotenv()

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)


async def enviar_mensaje_whatsapp(numero_destino: str, texto: str) -> None:
    url = f"https://graph.facebook.com/v17.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": numero_destino,
        "type": "text",
        "text": {"body": texto},
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload)
            print(f"[whatsapp] Respuesta enviada a {numero_destino} → HTTP {resp.status_code}")
    except Exception as e:
        print(f"[whatsapp] Error al enviar mensaje: {e}")


async def gestionar_consulta(pregunta: str, numero_remitente: str) -> None:
    respuesta = f"🔍 Modo consulta detectado. (Próximamente: Motor RAG para buscar: {pregunta})"
    await enviar_mensaje_whatsapp(numero_remitente, respuesta)


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

    value = (
        payload.get("entry", [{}])[0]
        .get("changes", [{}])[0]
        .get("value", {})
    )

    # Webhooks de estado (entregado, leído, etc.) — ignorar
    if not value.get("messages"):
        return Response(status_code=200)

    mensaje = value["messages"][0]
    numero_remitente: str = mensaje.get("from", "")
    texto: str = mensaje.get("text", {}).get("body") or str(mensaje)

    if texto.startswith("?"):
        pregunta = texto[1:].strip()
        await gestionar_consulta(pregunta, numero_remitente)
        return Response(status_code=200)

    nota_id = await insertar_nota(texto)
    print(f"[webhook] Nota #{nota_id} de {numero_remitente}: {texto[:80]}")
    await enviar_mensaje_whatsapp(numero_remitente, f"✅ Nota guardada: {texto}")

    return Response(status_code=200)
