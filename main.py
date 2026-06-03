import os
from typing import Any

import httpx
from groq import AsyncGroq
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from dotenv import load_dotenv

from db_manager import (
    guardar_nota,
    buscar_notas,
    borrar_todas_las_notas,
    obtener_notas_semana,
)

# override=True: el .env siempre gana sobre un valor obsoleto ya cargado en
# os.environ (evita que un token viejo quede cacheado entre recargas).
# En la nube (Render) no hay .env, así que esto es no-op y mandan sus env vars.
load_dotenv(override=True)

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
# Número propio al que se envía el resumen automático de los domingos.
MI_NUMERO = os.getenv("MI_NUMERO_WHATSAPP", "")
# Secreto que protege el endpoint que dispara el cron externo.
CRON_SECRET = os.getenv("CRON_SECRET", "")

app = FastAPI()


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
            if resp.status_code != 200:
                print(f"[whatsapp] Error HTTP {resp.status_code}: {resp.text}")
            else:
                print(f"[whatsapp] Respuesta enviada a {numero_destino} → HTTP {resp.status_code}")
    except Exception as e:
        print(f"[whatsapp] Error al enviar mensaje: {e}")


async def gestionar_consulta(pregunta: str, numero_remitente: str) -> None:
    notas = await buscar_notas(pregunta)
    contexto = "\n".join(f"- {n}" for n in notas) if notas else "(sin notas relevantes)"

    system_prompt = (
        "Eres el asistente personal del usuario en WhatsApp. "
        "Responde a su pregunta utilizando ÚNICAMENTE el siguiente contexto extraído de sus notas: "
        f"{contexto}. "
        "Sé directo, conciso y responde en español. "
        "Si la respuesta no está en el contexto, di que no tienes notas sobre eso."
    )

    cliente = AsyncGroq(api_key=GROQ_API_KEY)
    completion = await cliente.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": pregunta},
        ],
    )
    respuesta = completion.choices[0].message.content or "No se pudo generar respuesta."
    print(f"[rag] Consulta: {pregunta[:60]} | Contexto: {len(notas)} notas")
    await enviar_mensaje_whatsapp(numero_remitente, respuesta)


async def generar_resumen_semanal() -> str:
    """Resume con Groq las notas más importantes de la última semana."""
    notas = await obtener_notas_semana(7)
    if not notas:
        return "📭 No tienes notas de esta semana."

    listado = "\n".join(f"- {n}" for n in notas)
    system_prompt = (
        "Eres el asistente personal del usuario. A partir de sus notas de esta "
        "semana, redacta un resumen breve en español destacando SOLO las más "
        "importantes o accionables (recordatorios, tareas, ideas clave). Agrupa "
        "por temas si tiene sentido, usa viñetas y sé conciso. Ignora lo trivial."
    )
    cliente = AsyncGroq(api_key=GROQ_API_KEY)
    completion = await cliente.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Mis notas de esta semana:\n{listado}"},
        ],
    )
    cuerpo = completion.choices[0].message.content or "No se pudo generar el resumen."
    print(f"[resumen] Generado a partir de {len(notas)} notas")
    return f"🗓️ *Resumen de tu semana*\n\n{cuerpo}"


@app.get("/")
async def health_check() -> dict[str, str]:
    return {"status": "activo"}


async def _enviar_resumen_a(numero: str) -> None:
    resumen = await generar_resumen_semanal()
    await enviar_mensaje_whatsapp(numero, resumen)


@app.post("/tareas/resumen-semanal")
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


@app.get("/webhook")
async def verificar_webhook(request: Request) -> Response:
    params = request.query_params
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return Response(content=params.get("hub.challenge", ""), media_type="text/plain")
    raise HTTPException(status_code=403, detail="Token inválido")


# IDs de mensajes ya procesados, para ignorar reenvíos de Meta (entrega "al
# menos una vez"). En memoria: basta para una instancia; se vacía al reiniciar.
_procesados: set[str] = set()


async def procesar_mensaje(texto: str, numero_remitente: str) -> None:
    """Trabajo pesado (Upstash + Groq + envío). Se ejecuta tras devolver el 200."""
    if texto == "-@":
        await borrar_todas_las_notas()
        await enviar_mensaje_whatsapp(numero_remitente, "🗑️ Todas las notas han sido borradas.")
        return

    if texto == "+rs":
        resumen = await generar_resumen_semanal()
        await enviar_mensaje_whatsapp(numero_remitente, resumen)
        return

    if texto.startswith("?"):
        await gestionar_consulta(texto[1:].strip(), numero_remitente)
        return

    nota_id = await guardar_nota(texto)
    print(f"[webhook] Nota {nota_id} de {numero_remitente}: {texto[:80]}")
    await enviar_mensaje_whatsapp(numero_remitente, f"✅ Nota guardada: {texto}")


@app.post("/webhook")
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


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
