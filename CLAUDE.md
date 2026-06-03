# Contexto del Proyecto
Este es el MVP de "m.ai", un bot de WhatsApp que recibe mensajes, los procesa y actúa como gestor de conocimiento personal.
El objetivo final es integrarle IA Agéntica y capacidades RAG (bases de datos vectoriales).

# Stack Tecnológico
- Lenguaje: Python 3
- Backend/API: FastAPI
- Servidor ASGI: Uvicorn
- Base de datos (Fase 1): SQLite
- Entorno OS: Windows (PowerShell)

# Reglas de Entorno y Terminal (CRÍTICO)
- El entorno de trabajo es Windows. SIEMPRE debes usar comandos compatibles con PowerShell, nunca comandos exclusivos de bash/Linux (como `ls`, `rm` o `source`).
- Para activar el entorno virtual en PowerShell, el comando correcto es SIEMPRE: `.\venv\Scripts\Activate.ps1`
- Antes de instalar cualquier dependencia con `pip` o ejecutar `python main.py`, debes asegurarte de que el entorno virtual está activo.
- Actualiza el archivo `requirements.txt` cada vez que instales una nueva librería usando `pip freeze > requirements.txt`.

# Comandos de Desarrollo
- Arrancar el servidor en local: `uvicorn main:app --reload --port 8000`
- Instalar dependencias: `pip install -r requirements.txt`

# Convenciones de Código
- Usa tipado estático siempre que sea posible (Type Hints de Python).
- FastAPI: Mantén las rutas (endpoints) simples. La lógica pesada de procesamiento de notas debe ir en funciones separadas.
- Base de datos: Usa `sqlite3` de forma asíncrona o envuélvelo correctamente para no bloquear el Event Loop de FastAPI.
- Nunca pongas tokens, claves de API o contraseñas en el código fuente. Usa siempre el archivo `.env` y la librería `python-dotenv`.

# Flujo de Git
- Haz commits frecuentes y pequeños.
- Los mensajes de commit deben ser descriptivos, en español, y empezar con un verbo en infinitivo (ej. "Añadir endpoint para webhook", "Corregir error en base de datos").

# Reglas de Comportamiento y Eficiencia (Ahorro de Tokens)
- **Idioma:** Responde SIEMPRE en español de España, incluso si mi prompt, los logs de error o la documentación que lees están en inglés.
- **Concisión Extrema:** No des explicaciones teóricas largas ni me cuentes qué hace el código detalladamente
 a menos que te pida explícitamente "explica".
- **Cero Palabrería:** Elimina por completo las frases introductorias ("Aquí tienes el código", "Entendido", "Voy a hacer esto") y las conclusiones ("¿Necesitas ayuda con algo más?", "Espero que te sirva"). Ve directo al grano o a la acción.
- **Eficiencia de Código:** Si debes modificar un archivo largo, muestra solo el bloque de código que cambia (usando comentarios como `# ...resto del código...`) o utiliza tus herramientas internas de edición directa. Nunca imprimas un archivo completo en la consola a menos que sea estrictamente necesario.
- **Autonomía ante Errores:** Si ejecutas un comando de terminal y falla, no me pidas permiso para investigar. Lee el error, intenta aplicar una corrección y vuelve a ejecutar. Escríbeme solo cuando hayas tenido éxito o si llegas a un callejón sin salida absoluto.