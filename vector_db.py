import asyncio

import chromadb

_client = chromadb.PersistentClient(path="./chroma_data")
notas_collection = _client.get_or_create_collection(name="notas_collection")


async def guardar_en_vector(id_nota: str, texto: str) -> None:
    await asyncio.to_thread(
        notas_collection.add,
        documents=[texto],
        ids=[id_nota],
    )
    print(f"[chroma] Embedding guardado para nota #{id_nota}")
