from aiogram import html
from aiogram.fsm.scene import After, on
from aiogram.types import (
    CallbackQuery,
    KeyboardButton,
    Message,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from pymate.action_manager.telegram_policy.CancellableScene import CancellableScene, BUTTON_CANCEL
from pymate.action_manager.telegram_policy.FSMData import FSMData
from pymate.action_manager.telegram_policy.FinishScene import FinishScene


class StartAppScene(CancellableScene, state="start_app"):

    @on.message.enter()  # Marker for handler that should be called when a user enters the scene.
    async def on_enter(self, message: Message):
        markup = ReplyKeyboardBuilder()
        options = ["whatsapp", "telegram", "tinder", "tiktok", "drive", "photos", "calendar","whatsapp", "telegram", "tinder", "tiktok", "drive", "photos", "calendar","whatsapp", "telegram", "tinder", "tiktok", "drive", "photos", "calendar"]
        markup.add(*[KeyboardButton(text=item) for item in options])
        markup.add(BUTTON_CANCEL)
        return await message.answer(
            text="Choose the app to start",
            reply_markup=markup.adjust(2).as_markup(resize_keyboard=True),
        )

    @on.callback_query.enter()  # different types of updates that start the scene also supported.
    async def on_enter_callback(self, callback_query: CallbackQuery):
        await callback_query.answer()
        await self.on_enter(callback_query.message)

    @on.message.leave()  # Marker for handler that should be called when a user leaves the scene.
    async def on_leave(self, message: Message):
        data: FSMData = await self.wizard.get_data()
        selected_app = data.get("selected_app", "None")
        await message.answer(f"Selected app to start: {html.quote(selected_app)}!")

    @on.message(after=After.goto(FinishScene))
    async def input_selected_app(self, message: Message):
        await self.wizard.update_data(selected_app=message.text)