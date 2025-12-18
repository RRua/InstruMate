from aiogram import F
from aiogram import html
from aiogram.fsm.scene import After, on
from aiogram.types import (
    CallbackQuery,
    KeyboardButton,
    Message,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from pymate.action_manager.telegram_policy.CancellableScene import CancellableScene, BUTTON_CANCEL, BUTTON_FINISH, \
    BUTTON_BACK
from pymate.action_manager.telegram_policy.FSMData import FSMData
from pymate.action_manager.graph.UIActionUnit import SUB_ACTION_SCROLL_FLING_TO_START, SUB_ACTION_SCROLL_FLING_BACKWARD, \
    SUB_ACTION_SCROLL_FLING_FORWARD, SUB_ACTION_SCROLL_FLING_TO_END

INTERACT_TAP = "Tap"
INTERACT_AUTO_INPUT = "Auto input"
INTERACT_MOVE_NEXT = "Next"
INTERACT_KEY_BACK = "Android Back"
INTERACT_KEY_HOME = "Android Home"
INTERACT_KEY_ENTER = "Android Enter"
INTERACT_SCROLL_FLING_TO_START = "scroll:%s" % SUB_ACTION_SCROLL_FLING_TO_START
INTERACT_SCROLL_FLING_TO_END = "scroll:%s" % SUB_ACTION_SCROLL_FLING_TO_END
INTERACT_SCROLL_FLING_TO_FORWARD = "scroll:%s" % SUB_ACTION_SCROLL_FLING_FORWARD
INTERACT_SCROLL_FLING_BACKWARD = "scroll:%s" % SUB_ACTION_SCROLL_FLING_BACKWARD


class InteractScene(CancellableScene, state="interact"):

    async def send_current_action_unit_to_user(self, message: Message):
        from pymate.action_manager.telegram_policy.TelegramService import TelegramService
        telegram_service = TelegramService()
        prompt = telegram_service.get_prompt()
        if not prompt.is_solved():
            image = prompt.get_image()
            if image is not None:
                from aiogram.types import FSInputFile
                photo = FSInputFile(image)
                await message.reply_photo(photo)
            prompt_str = prompt.get_action_str()
            if prompt_str is None:
                await message.answer("No action to be done...")
            else:
                await message.answer(prompt_str)
                await message.answer(f"Type any text to be your input or choose {INTERACT_AUTO_INPUT}.")
                markup = ReplyKeyboardBuilder()
                options = [INTERACT_TAP, INTERACT_AUTO_INPUT, INTERACT_MOVE_NEXT, INTERACT_KEY_BACK, INTERACT_KEY_HOME,
                           INTERACT_KEY_ENTER, INTERACT_SCROLL_FLING_TO_FORWARD, INTERACT_SCROLL_FLING_BACKWARD,
                           INTERACT_SCROLL_FLING_TO_END, INTERACT_SCROLL_FLING_TO_START]
                markup.add(*[KeyboardButton(text=item) for item in options])
                markup.add(BUTTON_CANCEL)
                markup.add(BUTTON_BACK)
                markup.add(BUTTON_FINISH)
                return await message.answer(
                    text="Select your action:",
                    reply_markup=markup.adjust(3).as_markup(resize_keyboard=True),
                )
        else:
            markup = ReplyKeyboardBuilder()
            markup.add(BUTTON_CANCEL)
            markup.add(BUTTON_BACK)
            markup.add(BUTTON_FINISH)
            return await message.answer(
                text="There is no action to be done...",
                reply_markup=markup.adjust(3).as_markup(resize_keyboard=True),
            )

    @on.message.enter()
    async def on_enter(self, message: Message):
        await self.send_current_action_unit_to_user(message)

    @on.callback_query.enter()  # different types of updates that start the scene also supported.
    async def on_enter_callback(self, callback_query: CallbackQuery):
        await callback_query.answer()
        await self.on_enter(callback_query.message)

    @on.message.leave()  # Marker for handler that should be called when a user leaves the scene.
    async def on_leave(self, message: Message):
        data: FSMData = await self.wizard.get_data()
        selected_app = data.get("selected_app", "None")
        await message.answer(f"Selected app to start: {html.quote(selected_app)}!")

    @on.message()
    async def input_selected_app(self, message: Message):
        from pymate.action_manager.telegram_policy.TelegramService import TelegramService
        telegram_service = TelegramService()
        prompt = telegram_service.get_prompt()
        if message.text == INTERACT_TAP:
            prompt.set_action_tap()
        elif message.text == INTERACT_MOVE_NEXT:
            prompt.move_next()
        elif message.text == INTERACT_AUTO_INPUT:
            prompt.set_auto_input_text()
        elif message.text == INTERACT_KEY_BACK:
            prompt.set_action_key_back()
        elif message.text == INTERACT_KEY_HOME:
            prompt.set_action_key_home()
        elif message.text == INTERACT_KEY_ENTER:
            prompt.set_action_key_enter()
        elif message.text == INTERACT_SCROLL_FLING_BACKWARD:
            prompt.set_action_scroll(message.text.split(':')[1])
        elif message.text == INTERACT_SCROLL_FLING_TO_FORWARD:
            prompt.set_action_scroll(message.text.split(':')[1])
        elif message.text == INTERACT_SCROLL_FLING_TO_END:
            prompt.set_action_scroll(message.text.split(':')[1])
        elif message.text == INTERACT_SCROLL_FLING_TO_START:
            prompt.set_action_scroll(message.text.split(':')[1])
        else:
            prompt.set_input_text(message.text)
        await message.answer("Okay")
        await message.answer("Status:")
        await self.send_current_action_unit_to_user(message)

    async def do_cancel(self, message: Message):
        pass

    async def do_back(self, message: Message):
        from pymate.action_manager.telegram_policy.TelegramService import TelegramService
        telegram_service = TelegramService()
        prompt = telegram_service.get_prompt()
        prompt.move_back()
        await self.send_current_action_unit_to_user(message)

    async def do_finish(self, message: Message):
        from pymate.action_manager.telegram_policy.TelegramService import TelegramService
        telegram_service = TelegramService()
        prompt = telegram_service.get_prompt()
        prompt.set_solved(True)
        await message.answer("Prompt solved")
