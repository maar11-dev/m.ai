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


async def descargar_audio(media_id: str) -> bytes | None:
    """Descarga un audio de la API de WhatsApp (media_id → URL temporal → binario)."""
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    try:
        async with httpx.AsyncClient() as client:
            meta = await client.get(
                f"https://graph.facebook.com/v17.0/{media_id}", headers=headers
            )
            if meta.status_code != 200:
                print(f"[whatsapp] Error obteniendo URL del media {media_id}: HTTP {meta.status_code}: {meta.text}")
                return None
            url = meta.json().get("url")
            if not url:
                print(f"[whatsapp] Respuesta sin 'url' para media {media_id}")
                return None
            # La descarga del binario requiere el mismo Bearer token.
            audio = await client.get(url, headers=headers)
            if audio.status_code != 200:
                print(f"[whatsapp] Error descargando audio {media_id}: HTTP {audio.status_code}")
                return None
            return audio.content
    except Exception as e:
        print(f"[whatsapp] Error al descargar audio: {e}")
        return None
