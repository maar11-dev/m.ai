from app.db.vector import borrar_todas_las_notas, guardar_nota
from app.services.ai import (
    describir_imagen,
    generar_resumen_semanal,
    generar_tags,
    gestionar_consulta,
    transcribir_audio,
)
from app.services.whatsapp import descargar_media, enviar_mensaje_whatsapp

HELP_TEXT = (
    "📋 *Comandos disponibles*\n\n"
    "• Cualquier texto → guarda una nota\n"
    "• 🎤 Nota de voz → se transcribe y se guarda\n"
    "• 📷 Imagen → se describe con IA y se guarda\n"
    "• `? <pregunta>` → consulta tus notas con IA\n"
    "• `+rs` → resumen inteligente de la semana\n"
    "• `-@` → borra todas las notas\n"
    "• `/help` → muestra este mensaje"
)


async def procesar_imagen(
    media_id: str, mime_type: str, caption: str, numero_remitente: str
) -> None:
    """Descarga una imagen, la describe con visión y la guarda como nota."""
    await enviar_mensaje_whatsapp(numero_remitente, "📷 Imagen recibida, analizando...")
    imagen = await descargar_media(media_id)
    if not imagen:
        await enviar_mensaje_whatsapp(numero_remitente, "⚠️ No pude descargar la imagen. Inténtalo de nuevo.")
        return
    descripcion = await describir_imagen(imagen, mime_type, caption)
    if not descripcion:
        await enviar_mensaje_whatsapp(numero_remitente, "⚠️ No pude entender la imagen. Inténtalo de nuevo.")
        return
    texto = f"{caption}\n{descripcion}" if caption else descripcion
    tags = await generar_tags(texto)
    nota_id = await guardar_nota(texto, tags, user_id=numero_remitente)
    print(f"[webhook] Nota (imagen) {nota_id} de {numero_remitente}: {texto[:80]}")
    await enviar_mensaje_whatsapp(numero_remitente, f"✅ Imagen guardada como nota:\n{descripcion}")


async def procesar_audio(media_id: str, numero_remitente: str) -> None:
    """Descarga, transcribe y procesa una nota de voz como si fuera texto."""
    await enviar_mensaje_whatsapp(numero_remitente, "🎤 Audio recibido, transcribiendo...")
    audio = await descargar_media(media_id)
    if not audio:
        await enviar_mensaje_whatsapp(numero_remitente, "⚠️ No pude descargar el audio. Inténtalo de nuevo.")
        return
    texto = await transcribir_audio(audio)
    if not texto:
        await enviar_mensaje_whatsapp(numero_remitente, "⚠️ No pude entender el audio. ¿Puedes repetirlo?")
        return
    # Reutilizamos toda la lógica de texto: comandos, tags, fechas, guardado.
    await procesar_mensaje(texto, numero_remitente)


async def procesar_mensaje(texto: str, numero_remitente: str) -> None:
    """Trabajo pesado (Upstash + Groq + envío). Se ejecuta tras devolver el 200."""
    if texto == "/help":
        await enviar_mensaje_whatsapp(numero_remitente, HELP_TEXT)
        return

    if texto == "-@":
        await borrar_todas_las_notas(user_id=numero_remitente)
        await enviar_mensaje_whatsapp(numero_remitente, "🗑️ Todas las notas han sido borradas.")
        return

    if texto == "+rs":
        resumen = await generar_resumen_semanal(user_id=numero_remitente)
        await enviar_mensaje_whatsapp(numero_remitente, resumen)
        return

    if texto.startswith("?"):
        await gestionar_consulta(texto[1:].strip(), numero_remitente)
        return

    tags = await generar_tags(texto)
    nota_id = await guardar_nota(texto, tags, user_id=numero_remitente)
    print(f"[webhook] Nota {nota_id} de {numero_remitente}: {texto[:80]}")

    confirmacion = f"✅ Nota guardada: {texto}"
    await enviar_mensaje_whatsapp(numero_remitente, confirmacion)
