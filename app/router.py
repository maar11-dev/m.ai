from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response

from app.config import CRON_SECRET, MI_NUMERO, VERIFY_TOKEN
from app.db.vector import obtener_notas_con_evento
from app.services.ai import generar_resumen_semanal
from app.services.procesador import procesar_mensaje
from app.services.whatsapp import enviar_mensaje_whatsapp

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

    # Solo procesamos mensajes de texto reales. Reacciones, imágenes, stickers,
    # ubicaciones, etc. llegan por este mismo array y NO son notas que escribió
    # el usuario: se ignoran (antes el fallback guardaba el evento crudo).
    if mensaje.get("type") != "text":
        print(f"[webhook] Ignorado mensaje tipo '{mensaje.get('type')}'")
        return Response(status_code=200)

    # Anti-duplicado: Meta reenvía el mismo evento si el 200 tarda en llegar.
    msg_id = mensaje.get("id", "")
    if msg_id and msg_id in _procesados:
        print(f"[webhook] Duplicado ignorado: {msg_id}")
        return Response(status_code=200)
    if msg_id:
        if len(_procesados) > 2000:  # cota simple de memoria
            _procesados.clear()
        _procesados.add(msg_id)

    numero_remitente: str = mensaje.get("from", "")
    texto: str = (mensaje.get("text", {}).get("body") or "").strip()
    if not texto:
        return Response(status_code=200)

    # Respondemos 200 YA y procesamos en segundo plano: así Meta nunca agota el
    # tiempo de espera ni reintenta (evita respuestas/notas duplicadas).
    background_tasks.add_task(procesar_mensaje, texto, numero_remitente)
    return Response(status_code=200)


async def _enviar_resumen_a(numero: str) -> None:
    resumen = await generar_resumen_semanal()
    await enviar_mensaje_whatsapp(numero, resumen)


async def _enviar_recordatorios() -> None:
    fecha_objetivo = (date.today() + timedelta(days=2)).isoformat()
    notas = await obtener_notas_con_evento(fecha_objetivo)
    if not notas:
        print(f"[recordatorios] Ninguna nota con event_date={fecha_objetivo}")
        return
    for nota in notas:
        msg = (
            f"⏰ *Recordatorio* — tienes un evento en 2 días ({nota['event_date']}):\n\n"
            f"_{nota['texto']}_"
        )
        await enviar_mensaje_whatsapp(MI_NUMERO, msg)
        print(f"[recordatorios] Enviado recordatorio: {nota['texto'][:60]}")


@router.post("/tareas/recordatorios")
async def tarea_recordatorios(
    request: Request, background_tasks: BackgroundTasks
) -> dict[str, str]:
    """Endpoint para el cron diario que detecta eventos próximos y avisa."""
    if not CRON_SECRET or request.query_params.get("secret") != CRON_SECRET:
        raise HTTPException(status_code=403, detail="No autorizado")
    if not MI_NUMERO:
        raise HTTPException(status_code=500, detail="MI_NUMERO_WHATSAPP no configurado")
    background_tasks.add_task(_enviar_recordatorios)
    return {"status": "encolado"}


@router.post("/tareas/resumen-semanal")
async def tarea_resumen_semanal(
    request: Request, background_tasks: BackgroundTasks
) -> dict[str, str]:
    """Endpoint que dispara el cron externo los domingos. Protegido por secreto."""
    if not CRON_SECRET or request.query_params.get("secret") != CRON_SECRET:
        raise HTTPException(status_code=403, detail="No autorizado")
    if not MI_NUMERO:
        raise HTTPException(status_code=500, detail="MI_NUMERO_WHATSAPP no configurado")

    # Responde al instante y genera el resumen en segundo plano: así el cron
    # recibe su 200 enseguida y nunca choca con el límite de 30s de timeout.
    background_tasks.add_task(_enviar_resumen_a, MI_NUMERO)
    return {"status": "encolado"}
