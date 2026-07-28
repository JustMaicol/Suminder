import asyncio
from dotenv import load_dotenv

from config import TELEGRAM_BOT_TOKEN
from services.schedule import start_scheduler_loop
from services.telegram_service import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    start_handler,
    materias_handler,
    notas_handler,
    note_message_handler,
)

load_dotenv()


async def post_init(app):
    print("Activando servicio de alertas de horarios en segundo plano...")
    asyncio.create_task(start_scheduler_loop())


def main():
    print("Iniciando Suminder Bot")

    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler(["start", "help"], start_handler))
    app.add_handler(CommandHandler("materias", materias_handler))
    app.add_handler(CommandHandler("notas", notas_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, note_message_handler))

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
