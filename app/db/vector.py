import asyncio
import time
import uuid
from datetime import datetime, timezone

from upstash_vector import Index, Vector

# Index.from_env() lee UPSTASH_VECTOR_REST_URL y UPSTASH_VECTOR_REST_TOKEN.
# config.py ya llamó a load_dotenv() antes de que este módulo se importe.
index = Index.from_env()


async def guardar_nota(
    texto: str,
    tags: list[str] | None = None,
    user_id: str = "",
) -> str:
    id_unico = str(uuid.uuid4())
    ahora = time.time()
    metadata: dict = {
        "texto": texto,
        "created_at": ahora,
        "fecha_iso": datetime.fromtimestamp(ahora, timezone.utc).isoformat(),
        "tags": tags or [],
        "user_id": user_id,
    }
    await asyncio.to_thread(
        index.upsert,
        [Vector(id=id_unico, data=texto, metadata=metadata)],
    )
    print(f"[upstash] Nota guardada | id: {id_unico} | user: {user_id} | tags: {tags or []}")
    return id_unico


async def borrar_todas_las_notas(user_id: str = "") -> None:
    ids_a_borrar: list[str] = []
    cursor = ""
    while True:
        res = await asyncio.to_thread(
            index.range,
            cursor=cursor,
            limit=100,
            include_metadata=True,
        )
        for v in res.vectors:
            md = v.metadata or {}
            if md.get("user_id") == user_id:
                ids_a_borrar.append(v.id)
        cursor = res.next_cursor
        if not cursor:
            break

    if ids_a_borrar:
        await asyncio.to_thread(index.delete, ids_a_borrar)
    print(f"[upstash] Borradas {len(ids_a_borrar)} notas del usuario {user_id}")


async def obtener_notas_semana(dias: int = 7, user_id: str = "") -> list[str]:
    """Devuelve los textos de las notas del usuario creadas en los últimos `dias` días."""
    limite = time.time() - dias * 86400
    textos: list[str] = []
    cursor = ""
    while True:
        res = await asyncio.to_thread(
            index.range,
            cursor=cursor,
            limit=100,
            include_metadata=True,
        )
        for v in res.vectors:
            md = v.metadata or {}
            if md.get("user_id") != user_id:
                continue
            if md.get("texto") and md.get("created_at", 0) >= limite:
                textos.append(md["texto"])
        cursor = res.next_cursor
        if not cursor:
            break
    return textos


async def buscar_notas(
    pregunta: str,
    n_resultados: int = 10,
    tag_boost: str | None = None,
    user_id: str = "",
) -> list[str]:
    filtro = f"user_id = '{user_id}'" if user_id else None
    # Pedimos más candidatos de los necesarios para poder re-rankear por recencia y tag.
    candidatos = await asyncio.to_thread(
        index.query,
        data=pregunta,
        top_k=n_resultados * 3,
        include_metadata=True,
        filter=filtro,
    )

    ahora = time.time()
    HALF_LIFE_SEGUNDOS = 90 * 86400  # 30 días → 0.75×, 90+ días → mínimo 0.50×
    TAG_BOOST_FACTOR = 1.4  # notas con el tag relevante suben un 40% en el ranking

    def puntuacion(r) -> float:
        md = r.metadata or {}
        created_at = md.get("created_at", ahora)
        decay = max(1 / (1 + (ahora - created_at) / HALF_LIFE_SEGUNDOS), 0.5)
        score = r.score * decay
        if tag_boost and tag_boost in md.get("tags", []):
            score *= TAG_BOOST_FACTOR
        return score

    reordenados = sorted(candidatos, key=puntuacion, reverse=True)
    return [
        r.metadata["texto"]
        for r in reordenados[:n_resultados]
        if r.metadata and "texto" in r.metadata
    ]
