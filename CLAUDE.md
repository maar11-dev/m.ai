# Contexto del Proyecto
"m.ai" es un bot de WhatsApp multi-usuario que actúa como gestor de conocimiento personal con capacidades RAG. Cada usuario queda identificado por su número de teléfono; sus datos están aislados en Upstash Vector.

El objetivo es seguir añadiendo IA agéntica y mejorar las capacidades de búsqueda semántica.

# Stack Tecnológico
- **Lenguaje:** Python 3.12
- **Backend/API:** FastAPI + Uvicorn (ASGI)
- **Base de datos:** Upstash Vector (embeddings BGE-m3, REST API) — sin SQLite
- **LLM / Transcripción:** Groq API (`llama-3.1-8b-instant`, `whisper-large-v3-turbo`)
- **Mensajería:** Meta WhatsApp Cloud API v17.0
- **Despliegue:** Render.com (plan free, región Frankfurt)
- **Entorno local:** Windows (PowerShell)

# Arquitectura
```
app/
├── config.py          # Variables de entorno (load_dotenv)
├── router.py          # Endpoints FastAPI (/webhook GET+POST, /)
├── db/
│   └── vector.py      # Operaciones Upstash: guardar, buscar, borrar, resumen
└── services/
    ├── procesador.py  # Lógica de comandos y flujo principal
    ├── ai.py          # Groq: tags, RAG, resumen semanal, transcripción
    └── whatsapp.py    # Meta API: enviar mensajes, descargar audio
```

## Flujo de un mensaje
1. Meta envía POST /webhook → router filtra duplicados (set en memoria)
2. Se lanza `BackgroundTask` (responde 200 inmediato a Meta)
3. `procesador.py` evalúa el comando o guarda la nota
4. Todas las operaciones de BD incluyen `user_id=numero_remitente` para aislar datos

## Comandos del bot
| Comando | Acción |
|---------|--------|
| Cualquier texto | Genera tags (Groq) y guarda nota en Upstash |
| 🎤 Nota de voz | Transcribe (Whisper) y procesa como texto |
| 📷 Imagen | Describe con visión (Qwen3.6-27b) y guarda como nota |
| `? <pregunta>` | Búsqueda RAG semántica sobre las notas del usuario |
| `+rs` | Resumen semanal de los últimos 7 días |
| `-@` | Borra todas las notas del usuario |
| `/help` | Lista de comandos |

# Variables de Entorno
Configuradas en el panel de Render (no en el repo):
- `WHATSAPP_VERIFY_TOKEN` — token de verificación del webhook
- `WHATSAPP_ACCESS_TOKEN` — token permanente de la app Meta
- `WHATSAPP_PHONE_ID` — ID del número WhatsApp Business
- `GROQ_API_KEY`
- `UPSTASH_VECTOR_REST_URL`
- `UPSTASH_VECTOR_REST_TOKEN`

En local se leen desde `.env` (no versionado).

# Reglas de Entorno y Terminal (CRÍTICO)
- SIEMPRE usar PowerShell. Nunca comandos bash/Linux (`ls`, `rm`, `source`).
- Activar entorno virtual: `.\venv\Scripts\Activate.ps1`
- Activar antes de `pip install` o `python main.py`.
- Actualizar `requirements.txt` tras instalar: `pip freeze > requirements.txt`.

# Comandos de Desarrollo
- Servidor local: `uvicorn main:app --reload --port 8000`
- Dependencias: `pip install -r requirements.txt`

# Convenciones de Código
- Type hints en todo el código Python.
- Endpoints simples en `router.py`; lógica en `services/` y `db/`.
- Upstash Vector es la única fuente de verdad. No usar SQLite.
- Nunca poner tokens o claves en el código fuente. Siempre `.env` + `python-dotenv`.
- Todas las operaciones a Upstash deben ser async (usar `asyncio.to_thread` para el SDK síncrono).

# Flujo de Git
- Commits frecuentes y pequeños.
- Mensajes en español, comenzando con verbo en infinitivo (ej. "Añadir endpoint para webhook").

# Reglas de Comportamiento y Eficiencia (Ahorro de Tokens)
- **Idioma:** Responde SIEMPRE en español de España.
- **Concisión Extrema:** Sin explicaciones teóricas salvo que se pida "explica".
- **Cero Palabrería:** Sin frases introductorias ni conclusiones. Ve directo a la acción.
- **Eficiencia de Código:** Muestra solo el bloque que cambia o usa edición directa. Nunca imprimas un archivo completo salvo que sea estrictamente necesario.
- **Autonomía ante Errores:** Si un comando falla, investiga y corrige sin pedir permiso. Escribe solo al tener éxito o ante un callejón sin salida.
