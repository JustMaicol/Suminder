import difflib
import unicodedata
from database import supabase


def normalize_text(text: str) -> str:
    """Convierte texto a minúsculas y elimina tildes/acentos para comparaciones."""
    if not text:
        return ""
    text = text.lower().strip()
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


async def get_materias_all():
    response = supabase.table("materias").select("*").execute()
    return response.data if response.data else []


async def get_materia_aprox(user_search: str):

    materias = await get_materias_all()
    if not materias:
        return None

    search_norm = normalize_text(user_search)
    if not search_norm:
        return None

    # Nivel 1: Coincidencia Exacta
    for materia in materias:
        nombre_norm = normalize_text(materia.get("nombre", ""))
        if search_norm == nombre_norm:
            return materia

    # Nivel 2: Coincidencia por Subcadena
    for materia in materias:
        nombre_norm = normalize_text(materia.get("nombre", ""))
        if search_norm in nombre_norm or nombre_norm in search_norm:
            return materia

    # Nivel 3: Fuzzy Matching usando difflib para tolerancia a typos
    nombres_map = {normalize_text(m.get("nombre", "")): m for m in materias}
    nombres_list = list(nombres_map.keys())

    coincidencias = difflib.get_close_matches(search_norm, nombres_list, n=1, cutoff=0.3)

    if coincidencias:
        return nombres_map[coincidencias[0]]

    return None



async def get_notas_materia(materia_id: str | None):
    query = supabase.table("apuntes").select("id, materia_id, texto_original, resumen_ia, fecha_creacion")

    if materia_id is None:
        query = query.is_("materia_id", "null")
    else:
        query = query.eq("materia_id", materia_id)

    response = query.order("fecha_creacion", desc=True).execute()
    return response.data if response.data else []



async def save_note(materia_id: str | None, texto_original: str, resumen_ia: str):
    data = {
        "texto_original": texto_original,
        "resumen_ia": resumen_ia,
    }
    if materia_id:
        data["materia_id"] = materia_id

    response = supabase.table("apuntes").insert(data).execute()
    return response.data


from datetime import datetime
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("America/Managua")


async def get_materia_now():
    """Devuelve (materia_id, nombre_materia) de la clase en curso, o (None, None) si no hay ninguna."""
    now = datetime.now(TIMEZONE)
    dia_semana_num = now.weekday() + 1  # 1=Lunes .. 7=Domingo
    hora_actual_str = now.strftime("%H:%M:%S")

    try:
        response = (
            supabase.table("horarios")
            .select("materia_id, materias(nombre)")
            .eq("dia_semana", dia_semana_num)
            .lte("hora_inicio", hora_actual_str)
            .gte("hora_fin", hora_actual_str)
            .execute()
        )
        if response.data and len(response.data) > 0:
            item = response.data[0]
            materia_info = item.get("materias") or {}
            return item.get("materia_id"), materia_info.get("nombre")
    except Exception as e:
        print(f"Error al verificar materia activa: {e}")

    return None, None