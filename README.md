# m.ai

Bot de WhatsApp que actúa como gestor de conocimiento personal. Recibe mensajes, los almacena en SQLite y confirma el guardado respondiendo al remitente.

## Stack

- **Python 3** · **FastAPI** · **Uvicorn** · **SQLite** (`aiosqlite`) · **httpx**
- Integración con la **WhatsApp Cloud API (Meta)**

## Variables de entorno (`.env`)

```
WHATSAPP_VERIFY_TOKEN=   # Token para verificar el webhook con Meta
WHATSAPP_ACCESS_TOKEN=   # Token de acceso permanente de la app de Meta
WHATSAPP_PHONE_ID=       # ID del número de teléfono en Meta for Developers
```

## Arranque

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/webhook` | Verificación del webhook por Meta |
| `POST` | `/webhook` | Recibe mensajes de WhatsApp, los guarda y responde |
| `GET` | `/notas` | Lista todas las notas guardadas |
| `DELETE` | `/notas/{id}` | Elimina una nota por ID |

## Flujo principal

```
WhatsApp (usuario)
  └─► Meta Cloud API
        └─► POST /webhook  ──► SQLite (notas.db)
                           └─► Meta Cloud API ──► WhatsApp (confirmación ✅)
```
