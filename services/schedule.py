import asyncio
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo
from telegram import Bot

from config import TELEGRAM_BOT_TOKEN, MI_TELEGRAM_ID
from database import supabase

bot = Bot(token=TELEGRAM_BOT_TOKEN)

TIMEZONE = ZoneInfo("America/Managua")

_notified_hoy = set()  # claves "{horario_id}_{fecha}" ya notificadas
_ultima_fecha_revisada = None
_ultimo_chequeo = None  # datetime del ultimo chequeo exitoso


def get_current_now():
    return datetime.now(TIMEZONE)


def formatear_hora_12h(hora_str: str) -> str:
    """Convierte 'HH:MM:SS' o 'HH:MM' (24h) a formato de 12h con AM/PM, ej '1:00 PM'."""
    if not hora_str:
        return "?"
    partes = hora_str.split(":")
    hora, minuto = int(partes[0]), int(partes[1])
    t = dtime(hour=hora, minute=minuto)
    texto = t.strftime("%I:%M %p")
    return texto.lstrip("0")


async def check_schedule_alerts():
    global _ultima_fecha_revisada, _ultimo_chequeo

    now = get_current_now()
    fecha_actual_str = now.strftime("%Y-%m-%d")

    # Al cambiar el dia, se limpian las notificaciones ya enviadas y la ventana de chequeo
    if _ultima_fecha_revisada != fecha_actual_str:
        _notified_hoy.clear()
        _ultima_fecha_revisada = fecha_actual_str
        _ultimo_chequeo = None

    # Ventana de tiempo a revisar: desde el ultimo chequeo exitoso hasta ahora.
    # Esto evita que una demora del proceso (red lenta, reinicio, etc.) haga
    # que el bot se salte el minuto exacto de inicio de una clase.
    inicio_ventana = _ultimo_chequeo if _ultimo_chequeo else now
    dia_semana_num = now.weekday() + 1

    try:
        response = (
            supabase.table("horarios")
            .select("id, hora_inicio, hora_fin, aula, materia_id, materias(nombre, profesor)")
            .eq("dia_semana", dia_semana_num)
            .execute()
        )
        horarios = response.data if response.data else []
    except Exception as e:
        print(f"Error al consultar horarios en Supabase: {e}")
        return

    for item in horarios:
        hora_inicio_str = str(item.get("hora_inicio", ""))[:5]  # Formato HH:MM
        if not hora_inicio_str:
            continue

        hora, minuto = int(hora_inicio_str[:2]), int(hora_inicio_str[3:5])
        inicio_clase = now.replace(hour=hora, minute=minuto, second=0, microsecond=0)

        event_key = f"{item['id']}_{fecha_actual_str}"
        if event_key in _notified_hoy:
            continue

        # Se notifica si el inicio de la clase cae dentro de la ventana
        # (ultimo_chequeo, ahora], solo al INICIO de cada materia.
        if inicio_ventana < inicio_clase <= now:
            _notified_hoy.add(event_key)

            materia_info = item.get("materias", {}) or {}
            nombre_materia = materia_info.get("nombre", "Materia sin nombre")
            profesor = materia_info.get("profesor", "Profesor no asignado")
            aula = item.get("aula", "Sin aula asignada")
            hora_fin_str = str(item.get("hora_fin", ""))[:5]

            mensaje = (
                f"⏰ *¡Tu clase esta por comenzar!*\n\n"
                f"📚 *Materia:* {nombre_materia}\n"
                f"👨‍🏫 *Profesor:* {profesor}\n"
                f"🏫 *Aula:* {aula}\n"
                f"⏳ *Horario:* {formatear_hora_12h(hora_inicio_str)} - {formatear_hora_12h(hora_fin_str)}\n\n"
                f"💡 _Recuerda enviar tus apuntes por aquí para resumirlos._"
            )
            try:
                await bot.send_message(chat_id=MI_TELEGRAM_ID, text=mensaje, parse_mode="Markdown")
            except Exception as e:
                print(f"Error al enviar notificación de horario: {e}")

    _ultimo_chequeo = now


async def start_scheduler_loop():
    print("Servicio de Horarios activado en segundo plano (America/Managua)...")
    while True:
        try:
            await check_schedule_alerts()
        except Exception as e:
            print(f"Error en scheduler_loop: {e}")
        await asyncio.sleep(30)
