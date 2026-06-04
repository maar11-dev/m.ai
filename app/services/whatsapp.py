import httpx

from app.config import ACCESS_TOKEN, PHONE_ID


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
