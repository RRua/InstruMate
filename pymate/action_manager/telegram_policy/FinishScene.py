from aiogram.fsm.scene import After, Scene, on
from aiogram.types import (
    CallbackQuery,
    Message,
    ReplyKeyboardRemove,
)


class FinishScene(Scene, state="finish"):
    @on.message.enter()
    async def on_enter(self, message: Message):
        await message.answer("Finish line", reply_markup=ReplyKeyboardRemove())

    @on.callback_query.enter()
    async def on_enter_callback(self, callback_query: CallbackQuery):
        await callback_query.answer()
        await self.on_enter(callback_query.message)

    @on.message.leave()
    async def on_leave(self, message: Message):
        await message.answer("Finish line3", reply_markup=ReplyKeyboardRemove())

    @on.message(after=After.exit())
    async def on_message(self, message: Message):
        await message.answer("Finish line2", reply_markup=ReplyKeyboardRemove())