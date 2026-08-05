from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class AccessMiddleware(BaseMiddleware):
    def __init__(self, admin_id: int, user_id: int) -> None:
        self.admin_ids = {admin_id, user_id}

    async def __call__(
        self,
        handler: Callable[
            [TelegramObject, dict[str, Any]],
            Awaitable[Any],
        ],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)

        if user is None:
            return await handler(event, data)

        if user.id not in self.admin_ids:
            if isinstance(event, CallbackQuery):
                await event.answer(
                    "У вас нет доступа к этому боту.",
                    show_alert=True,
                )
            elif isinstance(event, Message):
                await event.answer(
                    "⛔ У вас нет доступа к этому боту."
                )

            return None

        data["is_admin"] = True

        return await handler(event, data)


class AdminOnlyMiddleware(BaseMiddleware):
    def __init__(self, admin_id: int, user_id: int) -> None:
        self.admin_ids = {admin_id, user_id}

    async def __call__(
        self,
        handler: Callable[
            [TelegramObject, dict[str, Any]],
            Awaitable[Any],
        ],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)

        if user is not None and user.id in self.admin_ids:
            return await handler(event, data)

        if isinstance(event, CallbackQuery):
            await event.answer(
                "Этот раздел доступен только администраторам.",
                show_alert=True,
            )
        elif isinstance(event, Message):
            await event.answer(
                "⛔ Этот раздел доступен только администраторам."
            )

        return None
