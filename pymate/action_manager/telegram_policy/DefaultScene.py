from aiogram import F
from aiogram.filters import Command
from aiogram.fsm.scene import After, Scene, on
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from pymate.action_manager.telegram_policy.StartAppScene import StartAppScene
from pymate.action_manager.telegram_policy.InteractScene import InteractScene


class DefaultScene(
    Scene,
    reset_data_on_enter=True,
    reset_history_on_enter=True,
    callback_query_without_state=True,
):

    @on.message(Command("start_app"))
    async def start_app(self, message: Message):
        await message.answer(
            "Are you sure?",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Yes, I want to start a new app.", callback_data="start_app")]]
            ),
        )

    @on.message(Command("interact"))
    async def interact(self, message: Message):
        from pymate.action_manager.telegram_policy.TelegramService import TelegramService
        telegram_service = TelegramService()
        prompt = telegram_service.get_prompt()
        pkg_name = prompt.get_pkg_name()
        image = prompt.get_image()
        if image is not None:
            from aiogram.types import FSInputFile
            photo = FSInputFile(image)
            await message.reply_photo(photo)
        await message.answer(
            f"Current app: {pkg_name}\n",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="Yes, I want to interact", callback_data="interact")]]
            ),
        )

    @on.callback_query(F.data == "start_app", after=After.goto(StartAppScene))
    async def start_app_callback(self, callback_query: CallbackQuery):
        await callback_query.answer(cache_time=0)
        await callback_query.message.delete_reply_markup()

    @on.callback_query(F.data == "interact", after=After.goto(InteractScene))
    async def interact_callback(self, callback_query: CallbackQuery):
        await callback_query.answer(cache_time=0)
        await callback_query.message.delete_reply_markup()

    @on.message.enter()
    @on.message()
    async def default_handler(self, message: Message):
        await message.answer(
            "Available commands:\n"
            "/start_app\n"
            "/interact",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="start_app")]],
                resize_keyboard=True,
            ),
        )
