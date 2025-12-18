from aiogram import F
from aiogram.fsm.scene import After, Scene, on
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardRemove,
)
from abc import abstractmethod


BUTTON_CANCEL = KeyboardButton(text="❌ Cancel")
BUTTON_BACK = KeyboardButton(text="🔙 Back")
BUTTON_FINISH = KeyboardButton(text="✅ Finish")


class CancellableScene(Scene):
    @on.message(F.text.casefold() == BUTTON_CANCEL.text.casefold(), after=After.exit())
    async def handle_cancel(self, message: Message):
        await self.do_cancel(message)
        await message.answer("Cancelled.", reply_markup=ReplyKeyboardRemove())

    @on.message(F.text.casefold() == BUTTON_BACK.text.casefold())
    async def handle_back(self, message: Message):
        await self.do_back(message)
        await message.answer("Back.")

    @on.message(F.text.casefold() == BUTTON_FINISH.text.casefold(), after=After.exit())
    async def handle_finish(self, message: Message):
        await self.do_finish(message)
        await message.answer("Finish.", reply_markup=ReplyKeyboardRemove())

    @abstractmethod
    async def do_cancel(self, message: Message):
        raise NotImplementedError()

    @abstractmethod
    async def do_back(self, message: Message):
        raise NotImplementedError()

    @abstractmethod
    async def do_finish(self, message: Message):
        raise NotImplementedError()

