import asyncio
import time
import uuid
from datetime import datetime, timezone

from upstash_vector import Index, Vector

# Index.from_env() lee UPSTASH_VECTOR_REST_URL y UPSTASH_VECTOR_REST_TOKEN.
# config.py ya llamó a load_dotenv() antes de que este módulo se importe.
index = Index.from_env()


async def guardar_nota(texto: str) -> str:
    id_unico = str(uuid.uuid4())
    ahora = time.time()
    metadata = {
        "texto": texto,
        "created_at": ahora,
        "fecha_iso": datetime.fromtimestamp(ahora, timezone.utc).isoformat(),
    }
    # data=texto → el modelo BGE-m3 de Upstash genera el embedding en su backend.
    await asyncio.to_thread(
        index.upsert,
        [Vector(id=id_unico, data=texto, metadata=metadata)],
    )
    print(f"[upstash] Nota guardada con id {id_unico}")
    return id_unico


async def borrar_todas_las_notas() -> None:
    await asyncio.to_thread(index.reset)
    print("[upstash] Índice reseteado — todas las notas borradas")


async def obtener_notas_semana(dias: int = 7) -> list[str]:
    """Devuelve los textos de las notas creadas en los últimos `dias` días."""
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
            if md.get("texto") and md.get("created_at", 0) >= limite:
                textos.append(md["texto"])
        cursor = res.next_cursor
        if not cursor:
            break
    return textos


async def buscar_notas(pregunta: str, n_resultados: int = 10) -> list[str]:
    # Pedimos más candidatos de los necesarios para poder re-rankear por recencia.
    candidatos = await asyncio.to_thread(
        index.query,
        data=pregunta,
        top_k=n_resultados * 3,
        include_metadata=True,
    )

    ahora = time.time()
    HALF_LIFE_SEGUNDOS = 90 * 86400  # 30 días → 0.75×, 90+ días → mínimo 0.50×

    def puntuacion(r) -> float:
        created_at = (r.metadata or {}).get("created_at", ahora)
        decay = max(1 / (1 + (ahora - created_at) / HALF_LIFE_SEGUNDOS), 0.5)
        return r.score * decay

    reordenados = sorted(candidatos, key=puntuacion, reverse=True)
    return [
        r.metadata["texto"]
        for r in reordenados[:n_resultados]
        if r.metadata and "texto" in r.metadata
    ]
