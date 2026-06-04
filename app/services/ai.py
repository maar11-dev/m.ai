from groq import AsyncGroq

from app.config import GROQ_API_KEY
from app.db.vector import buscar_notas, obtener_notas_semana
from app.services.whatsapp import enviar_mensaje_whatsapp


async def generar_tags(texto: str) -> list[str]:
    """Genera 1-3 etiquetas semánticas para clasificar la nota."""
    cliente = AsyncGroq(api_key=GROQ_API_KEY)
    completion = await cliente.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": (
                    "Genera entre 1 y 3 etiquetas en minúsculas para clasificar la nota. "
                    "Devuelve SOLO las etiquetas separadas por comas, sin explicación ni puntuación extra. "
                    "Ejemplos: 'música, pendiente' | 'libro' | 'idea, proyecto'"
                ),
            },
            {"role": "user", "content": texto},
        ],
        max_tokens=20,
    )
    raw = completion.choices[0].message.content or ""
    return [t.strip().lower() for t in raw.split(",") if t.strip()][:3]


async def extraer_tag_consulta(pregunta: str) -> str | None:
    """Extrae la etiqueta más relevante de una pregunta, si la hay."""
    cliente = AsyncGroq(api_key=GROQ_API_KEY)
    completion = await cliente.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": (
                    "Extrae la etiqueta principal de la pregunta si hay una categoría clara "
                    "(ej: música, libros, películas, tareas, ideas, recetas, compras...). "
                    "Devuelve SOLO la etiqueta en minúsculas o la palabra 'ninguna'."
                ),
            },
            {"role": "user", "content": pregunta},
        ],
        max_tokens=10,
    )
    raw = (completion.choices[0].message.content or "").strip().lower()
    return None if raw in ("ninguna", "none", "") else raw


async def gestionar_consulta(pregunta: str, numero_remitente: str) -> None:
    tag = await extraer_tag_consulta(pregunta)
    notas = await buscar_notas(pregunta, tag_boost=tag)
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
    print(f"[rag] Consulta: {pregunta[:60]} | tag: {tag} | contexto: {len(notas)} notas")
    await enviar_mensaje_whatsapp(numero_remitente, respuesta)


async def generar_resumen_semanal() -> str:
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
