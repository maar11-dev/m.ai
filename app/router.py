from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response

from app.services.procesador import procesar_audio, procesar_imagen, procesar_mensaje
from app.config import VERIFY_TOKEN

router = APIRouter()

# IDs de mensajes ya procesados, para ignorar reenvíos de Meta (entrega "al
# menos una vez"). En memoria: basta para una instancia; se vacía al reiniciar.
_procesados: set[str] = set()


@router.get("/")
async def health_check() -> dict[str, str]:
    return {"status": "activo"}


@router.get("/webhook")
async def verificar_webhook(request: Request) -> Response:
    params = request.query_params
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return Response(content=params.get("hub.challenge", ""), media_type="text/plain")
    raise HTTPException(status_code=403, detail="Token inválido")


@router.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks) -> Response:
    payload: dict[str, Any] = await request.json()

    value = (
        payload.get("entry", [{}])[0]
        .get("changes", [{}])[0]
        .get("value", {})
    )

    mensajes = value.get("messages")
    # Webhooks de estado (entregado, leído, etc.) o sin mensajes — ignorar.
    if not mensajes:
        return Response(status_code=200)

    mensaje = mensajes[0]

    # Solo procesamos texto, notas de voz e imágenes. Reacciones, stickers,
    # ubicaciones, etc. llegan por este mismo array y NO son notas que escribió
    # el usuario: se ignoran (antes el fallback guardaba el evento crudo).
    tipo = mensaje.get("type")
    if tipo not in ("text", "audio", "image"):
        print(f"[webhook] Ignorado mensaje tipo '{tipo}'")
        return Response(status_code=200)

    numero_remitente: str = mensaje.get("from", "")

    # Anti-duplicado: Meta reenvía el mismo evento si el 200 tarda en llegar.
    msg_id = mensaje.get("id", "")
    if msg_id and msg_id in _procesados:
        print(f"[webhook] Duplicado ignorado: {msg_id}")
        return Response(status_code=200)
    if msg_id:
        if len(_procesados) > 2000:  # cota simple de memoria
            _procesados.clear()
        _procesados.add(msg_id)

    # Respondemos 200 YA y procesamos en segundo plano: así Meta nunca agota el
    # tiempo de espera ni reintenta (evita respuestas/notas duplicadas).
    if tipo == "audio":
        media_id = mensaje.get("audio", {}).get("id", "")
        if not media_id:
            return Response(status_code=200)
        background_tasks.add_task(procesar_audio, media_id, numero_remitente)
        return Response(status_code=200)

    if tipo == "image":
        imagen = mensaje.get("image", {})
        media_id = imagen.get("id", "")
        if not media_id:
            return Response(status_code=200)
        mime_type = imagen.get("mime_type", "image/jpeg")
        caption = (imagen.get("caption") or "").strip()
        background_tasks.add_task(procesar_imagen, media_id, mime_type, caption, numero_remitente)
        return Response(status_code=200)

    texto: str = (mensaje.get("text", {}).get("body") or "").strip()
    if not texto:
        return Response(status_code=200)

    background_tasks.add_task(procesar_mensaje, texto, numero_remitente)
    return Response(status_code=200)


