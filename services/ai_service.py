from config import GEMINI_API_KEY
from google import genai
from google.genai import types

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

NOT_RELATED = "NOT_RELATED"


def build_system_prompt(materia: str | None) -> str:
    """Arma el prompt segun la materia activa. Cada materia puede ser de cualquier
    indole (programacion, calculo, redes, RRHH, proyectos, etc.), asi que el resumen
    debe adaptarse al tema en vez de asumir siempre contenido tecnico de informatica."""
    if materia:
        return f"""Eres un asistente que ayuda a un estudiante a recordar lo que se explico hoy en su clase de "{materia}".

REGLAS:
- Responde con un resumen CORTO (2 a 5 lineas), en lenguaje simple y natural, como si le contaras a un compañero lo que vieron hoy en esa clase.
- Ejemplo de tono: "Hoy explicaron sobre los webhooks: son ..." o "Hoy vieron distribución normal: es una forma de...".
- Adapta el contenido y el vocabulario al tipo de materia. "{materia}" puede ser de programación, matemática/cálculo, redes, recursos humanos, gestión de proyectos, u otra área — no asumas que siempre es un tema técnico de informática.
- El texto de entrada debe tratar sobre contenido académico relacionado con la materia "{materia}". Si el texto NO tiene relación alguna con esa materia (por ejemplo, comentarios personales, cotidianos, o de un tema totalmente distinto sin conexión con "{materia}"), responde EXCLUSIVAMENTE con la palabra: {NOT_RELATED}
- No agregues saludos, preámbulos, ni texto adicional fuera del resumen."""

    return """Eres un asistente que ayuda a un estudiante a condensar una nota en un resumen breve y fácil de entender.

REGLAS:
- Responde con un resumen CORTO (2 a 5 lineas), en lenguaje simple y natural.
- No hay una materia específica asociada a esta nota (fue escrita fuera de horario de clase), así que resume el contenido tal cual venga, sin rechazarlo por tema.
- No agregues saludos, preámbulos, ni texto adicional fuera del resumen."""


async def resumen(note_text: str, materia: str | None = None) -> str | None:
    print(f"[Gemini IA] Procesando apunte ({len(note_text)} caracteres) para materia '{materia}'... Esperando respuesta de la IA...")
    try:
        config = types.GenerateContentConfig(
            system_instruction=build_system_prompt(materia),
            temperature=0.2,
            max_output_tokens=512,
        )
        interaction = await gemini_client.aio.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=note_text,
            config=config,
        )
        texto_resultado = (interaction.text or "").strip()
        print("[Gemini IA] Resumen recibido exitosamente de Google Gemini.")

        if texto_resultado.upper().startswith(NOT_RELATED):
            return NOT_RELATED

        return texto_resultado
    except Exception as e:
        print(f"[Gemini IA Error] Fallo en la llamada a la API: {e}")
        return None