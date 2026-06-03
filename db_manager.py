import asyncio
import uuid

from dotenv import load_dotenv
from upstash_vector import Index, Vector

# Carga .env antes de inicializar para que from_env() vea las credenciales,
# independientemente del orden de importación de los módulos.
load_dotenv(override=True)

# Cliente global. Lee UPSTASH_VECTOR_REST_URL y UPSTASH_VECTOR_REST_TOKEN del entorno.
index = Index.from_env()


async def guardar_nota(texto: str) -> str:
    id_unico = str(uuid.uuid4())
    # data=texto -> el modelo BGE-m3 de Upstash genera el embedding en su backend.
    await asyncio.to_thread(
        index.upsert,
        [Vector(id=id_unico, data=texto, metadata={"texto": texto})],
    )
    print(f"[upstash] Nota guardada con id {id_unico}")
    return id_unico


async def borrar_todas_las_notas() -> None:
    await asyncio.to_thread(index.reset)
    print("[upstash] Índice reseteado — todas las notas borradas")


async def buscar_notas(pregunta: str, n_resultados: int = 10) -> list[str]:
    resultados = await asyncio.to_thread(
        index.query,
        data=pregunta,
        top_k=n_resultados,
        include_metadata=True,
    )
    return [
        r.metadata["texto"]
        for r in resultados
        if r.metadata and "texto" in r.metadata
    ]
