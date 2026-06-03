import aiosqlite
from datetime import datetime

DB_PATH = "notas.db"


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS notas (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha             TEXT    NOT NULL,
                texto_del_mensaje TEXT    NOT NULL,
                procesado         BOOLEAN NOT NULL DEFAULT 0
            )
            """
        )
        await db.commit()


async def obtener_notas() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM notas ORDER BY id DESC")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def eliminar_nota(nota_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM notas WHERE id = ?", (nota_id,))
        await db.commit()
        return cursor.rowcount > 0


async def insertar_nota(texto: str) -> int:
    fecha = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO notas (fecha, texto_del_mensaje) VALUES (?, ?)",
            (fecha, texto),
        )
        await db.commit()
        return cursor.lastrowid
