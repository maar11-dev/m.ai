# m.ai

Bot de WhatsApp que actúa como gestor de conocimiento personal con IA y RAG. Recibe mensajes de texto, los almacena en una base de datos vectorial y permite consultarlos con lenguaje natural.

## Stack

- **Python 3** · **FastAPI** · **Uvicorn** · **httpx**
- **Upstash Vector** — base de datos vectorial (embeddings BGE-m3)
- **Groq API** — LLM (`llama-3.1-8b-instant`) para consultas RAG y resúmenes
- **WhatsApp Cloud API (Meta)** — canal de entrada/salida

## Variables de entorno (`.env`)

```
WHATSAPP_VERIFY_TOKEN=       # Token para verificar el webhook con Meta
WHATSAPP_ACCESS_TOKEN=       # Token de acceso permanente de la app Meta
WHATSAPP_PHONE_ID=           # ID del número en Meta for Developers
GROQ_API_KEY=                # API key de Groq
UPSTASH_VECTOR_REST_URL=     # URL REST de la base vectorial Upstash
UPSTASH_VECTOR_REST_TOKEN=   # Token de autenticación Upstash
MI_NUMERO_WHATSAPP=          # Tu número (formato internacional, ej: 34612345678)
CRON_SECRET=                 # Secreto para proteger el endpoint de cron
```

## Arranque local

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Para exponer el webhook a Meta en desarrollo, usar Cloudflare Tunnel:

```powershell
.\cloudflared.exe tunnel --url http://localhost:8000
```

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/webhook` | Verificación del webhook por Meta |
| `POST` | `/webhook` | Recibe y procesa mensajes de WhatsApp |
| `POST` | `/tareas/resumen-semanal` | Dispara el resumen semanal (requiere `CRON_SECRET`) |

## Comandos del bot (vía WhatsApp)

| Mensaje | Acción |
|---------|--------|
| Texto normal | Guarda la nota en Upstash Vector |
| `? <pregunta>` | Consulta RAG: busca notas relevantes y responde con IA |
| `+rs` | Genera un resumen inteligente de las notas de los últimos 7 días |
| `-@` | Borra todas las notas del índice vectorial |

## Flujo principal

```
WhatsApp (usuario)
  └─► Meta Cloud API
        └─► POST /webhook
              ├─► [texto normal] Upstash Vector (guardar embedding)
              │                       └─► WhatsApp (confirmación ✅)
              │
              ├─► [? pregunta]   Upstash Vector (búsqueda semántica)
              │                       └─► Groq LLM (respuesta RAG)
              │                             └─► WhatsApp (respuesta)
              │
              └─► [+rs]          Upstash Vector (notas 7 días)
                                      └─► Groq LLM (resumen)
                                            └─► WhatsApp (resumen)
```

El procesamiento pesado (IA, base de datos) corre en background con `BackgroundTasks` de FastAPI para responder a Meta en < 5 s y evitar reintentos.

## Despliegue

Configurado para **Render.com** (`render.yaml`): Python 3.12, región Frankfurt, plan free. Las variables de entorno se configuran en el panel de Render, nunca en el YAML.
