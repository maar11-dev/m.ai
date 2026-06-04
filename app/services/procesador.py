import asyncio

from app.db.vector import borrar_todas_las_notas, guardar_nota
from app.services.ai import (
    extraer_fecha_evento,
    generar_resumen_semanal,
    generar_tags,
    gestionar_consulta,
)
from app.services.whatsapp import enviar_mensaje_whatsapp

HELP_TEXT = (
    "📋 *Comandos disponibles*\n\n"
    "• Cualquier texto → guarda una nota\n"
    "• `? <pregunta>` → consulta tus notas con IA\n"
    "• `+rs` → resumen inteligente de la semana\n"
    "• `-@` → borra todas las notas\n"
    "• `/help` → muestra este mensaje"
)


async def procesar_mensaje(texto: str, numero_remitente: str) -> None:
    """Trabajo pesado (Upstash + Groq + envío). Se ejecuta tras devolver el 200."""
    if texto == "/help":
        await enviar_mensaje_whatsapp(numero_remitente, HELP_TEXT)
        return

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

    # Tags y fecha de evento en paralelo — una sola ronda de llamadas a Groq.
    tags, event_date = await asyncio.gather(generar_tags(texto), extraer_fecha_evento(texto))
    nota_id = await guardar_nota(texto, tags, event_date)
    print(f"[webhook] Nota {nota_id} de {numero_remitente}: {texto[:80]}")

    tags_str = " ".join(f"#{t}" for t in tags) if tags else ""
    fecha_str = f"\n📅 Recordatorio programado para el {event_date}" if event_date else ""
    confirmacion = f"✅ Nota guardada {tags_str}{fecha_str}\n_{texto}_" if tags_str else f"✅ Nota guardada{fecha_str}: {texto}"
    await enviar_mensaje_whatsapp(numero_remitente, confirmacion)
