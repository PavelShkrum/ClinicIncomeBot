import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import load_config
from database.db import init_db
from handlers.account import router as account_router
from handlers.appointments import router as appointments_router
from handlers.clinics import router as clinics_router
from handlers.history import router as history_router
from handlers.specialties import router as specialties_router
from handlers.start import router as start_router
from handlers.statistics import router as statistics_router
from middlewares.access import AccessMiddleware, AdminOnlyMiddleware


async def main() -> None:
    config = load_config()

    await init_db()

    bot = Bot(token=config.bot_token)

    dispatcher = Dispatcher(
        storage=MemoryStorage(),
    )

    access_middleware = AccessMiddleware(
        admin_id=config.admin_id,
        user_id=config.user_id,
    )

    dispatcher.message.outer_middleware(access_middleware)
    dispatcher.callback_query.outer_middleware(access_middleware)

    admin_middleware = AdminOnlyMiddleware(
        admin_id=config.admin_id,
        user_id=config.user_id,
    )

    clinics_router.message.middleware(admin_middleware)
    clinics_router.callback_query.middleware(admin_middleware)
    specialties_router.message.middleware(admin_middleware)
    specialties_router.callback_query.middleware(admin_middleware)

    dispatcher.include_router(account_router)
    dispatcher.include_router(clinics_router)
    dispatcher.include_router(specialties_router)
    dispatcher.include_router(appointments_router)
    dispatcher.include_router(statistics_router)
    dispatcher.include_router(history_router)
    dispatcher.include_router(start_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
