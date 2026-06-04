import os

from dotenv import load_dotenv

# override=True: el .env siempre gana sobre un valor obsoleto ya cargado en
# os.environ (evita que un token viejo quede cacheado entre recargas).
# En la nube (Render) no hay .env, así que esto es no-op y mandan sus env vars.
load_dotenv(override=True)

VERIFY_TOKEN: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
ACCESS_TOKEN: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
PHONE_ID: str = os.getenv("WHATSAPP_PHONE_ID", "")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
MI_NUMERO: str = os.getenv("MI_NUMERO_WHATSAPP", "")
CRON_SECRET: str = os.getenv("CRON_SECRET", "")
