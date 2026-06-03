import os
from typing import Any

import httpx
from groq import AsyncGroq
from fastapi import FastAPI, HTTPException, Request, Response
from dotenv import load_dotenv

from db_manager import guardar_nota, buscar_notas

# override=True: el .env siempre gana sobre un valor obsoleto ya cargado en
# os.environ (evita que un token viejo quede cacheado entre recargas).
# En la nube (Render) no hay .env, así que esto es no-op y mandan sus env vars.
load_dotenv(override=True)

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

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


@app.get("/")
async def health_check() -> dict[str, str]:
    return {"status": "activo"}


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

    nota_id = await guardar_nota(texto)
    print(f"[webhook] Nota {nota_id} de {numero_remitente}: {texto[:80]}")
    await enviar_mensaje_whatsapp(numero_remitente, f"✅ Nota guardada: {texto}")

    return Response(status_code=200)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
