from config import GEMINI_API_KEY
from google import genai
from google.genai import types

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """Eres un sintetizador técnico de informática. Transformas notas informales de estudio en resúmenes estructurados en Markdown.

REGLAS:
- Responde SOLO con el esquema Markdown. Sin preámbulos, saludos ni cierres.
- Si la entrada no contiene contenido técnico de informática, responde: "No se detectó contenido técnico para resumir."
- Si una sección del esquema no aplica a la entrada, omítela. No rellenes con contenido genérico.
- Si la entrada menciona herramientas o comandos, incluye su rol en el flujo.

ESQUEMA:

## [Tema / Tecnología]

**1. Definición y Propósito**
- **¿Qué es?:** [1-2 oraciones técnicas]
- **Problema que resuelve:** [Justificación de existencia]

**2. Componentes Clave**
- **[Componente]:** [Función en contexto]

**3. Flujo / Aplicación**
1. [Paso o comando clave]

**4. Caso de Uso**
- [Escenario óptimo de aplicación]

EJEMPLO:
Entrada: "hoy vi como se disenia un sistema de informacion"
Salida: ## Diseño de Sistemas de Información
**1. Definición y Propósito**
- **¿Qué es?:** Proceso de definir arquitectura, módulos e interfaces de un sistema para satisfacer requisitos específicos.
[...resto del esquema aplicado]"""

RESUMEN_CONFIG = types.GenerateContentConfig(
    system_instruction=SYSTEM_PROMPT,
    temperature=0.2,
    max_output_tokens=1024,
)


async def resumen(note_text: str) -> str | None:
    print(f"[Gemini IA] Procesando apunte ({len(note_text)} caracteres)... Esperando respuesta de la IA...")
    try:
        interaction = await gemini_client.aio.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=note_text,
            config=RESUMEN_CONFIG,
        )
        print("[Gemini IA] Resumen recibido exitosamente de Google Gemini.")
        return interaction.text
    except Exception as e:
        print(f"[Gemini IA Error] Fallo en la llamada a la API: {e}")
        return None