import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import TELEGRAM_BOT_TOKEN, MI_TELEGRAM_ID
from services.ai_service import resumen, NOT_RELATED
from services.database_service import (
    get_materias_all,
    get_materia_aprox,
    get_notas_materia,
    save_note,
    get_materia_now,
)


async def delete_message_later(message, delay_seconds: int = 600):
    await asyncio.sleep(delay_seconds)
    try:
        await message.delete()
    except Exception as e:
        print(f"Error al auto-eliminar mensaje: {e}")


def usuario_autorizado(update: Update) -> bool:
    user_id = update.effective_user.id if update.effective_user else None
    return str(user_id) == str(MI_TELEGRAM_ID)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if not usuario_autorizado(update):
        await update.message.reply_text("⛔ No tienes acceso a Suminder.")
        return

    help_message = (
        "🤖 *¡Hola! Soy Suminder, tu asistente de notas de clase.*\n\n"
        "Puedes usar estos comandos:\n"
        "• `/notas <materia>` — Ver resúmenes de una materia (Ej: `/notas programacion`).\n"
        "• `/notas general` — Ver notas guardadas fuera de clase.\n"
        "• `/materias` — Listar todas tus materias registradas.\n"
        "• *Cualquier otro texto* — Se generará un resumen automático de la clase actual."
    )
    await update.message.reply_text(help_message, parse_mode="Markdown")


async def materias_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if not usuario_autorizado(update):
        return

    materias = await get_materias_all()
    if not materias:
        await update.message.reply_text("📌 No tienes materias registradas aún en Supabase.")
        return

    lista_str = "\n".join([f"• `{m.get('nombre')}`" for m in materias])
    await update.message.reply_text(f"📚 *Tus Materias Registradas:*\n\n{lista_str}", parse_mode="Markdown")


async def notas_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if not usuario_autorizado(update):
        return

    if not context.args:
        await update.message.reply_text(
            "⚠️ *Debes especificar la materia o tipo de nota.*\n\n"
            "*Ejemplos:*\n"
            "• `/notas programacion` — Ver notas de una clase.\n"
            "• `/notas general` — Ver notas guardadas fuera de horario.",
            parse_mode="Markdown",
        )
        return

    termino_busqueda = " ".join(context.args).strip()
    termino_norm = termino_busqueda.lower()

    if termino_norm in ["general", "generales", "varias", "extra", "libres", "sin materia"]:
        nombre_real = "Notas Generales (Fuera de clase)"
        notas = await get_notas_materia(None)
    else:
        materia_encontrada = await get_materia_aprox(termino_busqueda)
        if not materia_encontrada:
            await update.message.reply_text(
                f"❌ No encontré ninguna materia similar a *'{termino_busqueda}'*.\n\n"
                f"💡 _Tip: Para ver notas sin clase asociada escribe_ `/notas general`.",
                parse_mode="Markdown",
            )
            return

        nombre_real = materia_encontrada.get("nombre")
        materia_id = materia_encontrada.get("id")
        notas = await get_notas_materia(materia_id)

    if not notas:
        await update.message.reply_text(
            f"📌 No tienes apuntes guardados en *{nombre_real}* aún.",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(
        f"📚 *Apuntes encontrados para {nombre_real}:* ({len(notas)} nota{'s' if len(notas) != 1 else ''})",
        parse_mode="Markdown",
    )

    for idx, nota in enumerate(notas[:5], 1):
        fecha = str(nota.get("fecha_creacion", ""))[:10]
        resumen_txt = nota.get("resumen_ia", "")
        msg = f"🗓 *Nota #{idx} ({fecha})*\n\n{resumen_txt}"
        await update.message.reply_text(msg, parse_mode="Markdown")


async def note_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    if not usuario_autorizado(update):
        return

    texto = update.message.text.strip()
    print(f"\n[Telegram Long Polling] Apunte recibido: '{texto[:40]}...'")

    materia_id, materia_nombre = await get_materia_now()

    resumen_ia = await resumen(texto, materia_nombre)
    if not resumen_ia:
        await update.message.reply_text(
            "⚠️ *No se pudo generar el resumen.* Ocurrió un problema con la IA, por lo que la nota no ha sido guardada.",
            parse_mode="Markdown",
        )
        return

    if resumen_ia == NOT_RELATED:
        await update.message.reply_text(
            f"🤔 *Ese mensaje no parece tener relación con la clase actual ({materia_nombre}).*\n\n"
            f"No lo guardé como apunte. Si es una nota aparte, escríbela fuera del horario de clase.",
            parse_mode="Markdown",
        )
        return

    await save_note(materia_id, texto, resumen_ia)

    if materia_id:
        respuesta = (
            f"📝 *Resumen guardado exitosamente*\n\n{resumen_ia}\n\n"
            f"⏱ _Este mensaje se auto-eliminará en 10 minutos para mantener limpio el chat._"
        )
    else:
        respuesta = (
            f"📝 *Resumen generado (Fuera de horario de clase)*\n\n{resumen_ia}\n\n"
            f"ℹ️ _Se guardó como nota general._\n"
            f"⏱ _Este mensaje se auto-eliminará en 10 minutos para mantener limpio el chat._"
        )

    bot_msg = await update.message.reply_text(respuesta, parse_mode="Markdown")
    asyncio.create_task(delete_message_later(bot_msg, delay_seconds=600))
