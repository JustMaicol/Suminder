import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Bot

from config import TELEGRAM_BOT_TOKEN, MI_TELEGRAM_ID
from database import supabase

bot = Bot(token=TELEGRAM_BOT_TOKEN)

TIMEZONE = ZoneInfo("America/Managua")

_notified_today = set()


def get_current_now():
    return datetime.now(TIMEZONE)


async def check_schedule_alerts():
    now = get_current_now()
    dia_semana_num = now.weekday() + 1
    hora_actual_str = now.strftime("%H:%M")
    fecha_actual_str = now.strftime("%Y-%m-%d")

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
        materia_info = item.get("materias", {}) or {}
        nombre_materia = materia_info.get("nombre", "Materia sin nombre")
        profesor = materia_info.get("profesor", "Profesor no asignado")
        aula = item.get("aula", "Sin aula asignada")
        hora_fin = str(item.get("hora_fin", ""))[:5]  # Formato HH:MM
        hora_inicio = str(item.get("hora_inicio", ""))[:5]

        # Clave única para evitar notificar dos veces la misma alarma hoy
        event_key = f"{item['id']}_{fecha_actual_str}_{hora_actual_str}"

        if event_key in _notified_today:
            continue

        # Si estamos exactamente en la hora de aviso / fin de clase (ej. 14:40)
        if hora_actual_str == hora_fin or hora_actual_str == hora_inicio:
            _notified_today.add(event_key)

            mensaje = (
                f"⏰ *Recordatorio de Horario de Clase*\n\n"
                f"📚 *Materia:* {nombre_materia}\n"
                f"👨‍🏫 *Profesor:* {profesor}\n"
                f"🏫 *Aula:* {aula}\n"
                f"⏳ *Horario:* {hora_inicio} - {hora_fin}\n\n"
                f"💡 _Recuerda enviar tus apuntes por aquí para resumirlos._"
            )
            try:
                await bot.send_message(chat_id=MI_TELEGRAM_ID, text=mensaje, parse_mode="Markdown")
            except Exception as e:
                print(f"Error al enviar notificación de horario: {e}")



async def start_scheduler_loop():
    print("Servicio de Horarios activado en segundo plano (America/Managua)...")
    while True:
        try:
            await check_schedule_alerts()
        except Exception as e:
            print(f"Error en scheduler_loop: {e}")
        await asyncio.sleep(30)
