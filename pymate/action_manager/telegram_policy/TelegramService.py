import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.scene import SceneRegistry
from pymate.action_manager.telegram_policy.DefaultScene import DefaultScene
from pymate.action_manager.telegram_policy.StartAppScene import StartAppScene
from pymate.action_manager.telegram_policy.InteractScene import InteractScene
from pymate.action_manager.telegram_policy.FinishScene import FinishScene
from pymate.action_manager.telegram_policy.TelegramPrompt import TelegramPrompt
from threading import Thread, Lock
import queue
from os import getenv


class TelegramService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(TelegramService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.logger = logging.getLogger(self.__class__.__name__)
            self.service_thread = None
            self.dispatcher = None
            self.channel_id = getenv('TELEGRAM_CHANNEL_ID')
            self.bot_token = getenv('TELEGRAM_BOT_TOKEN')
            self.create_dispatcher()
            self.bot = Bot(self.bot_token)
            self.force_quit = False
            self.event_loop = None
            self.channel_lock = Lock()
            self.channel_queue = queue.Queue()
            self.prompt_lock = Lock()
            self.prompt = None
            self.prompt_solved = False
            self.initialized = True
            self.started = False

    def create_dispatcher(self):
        dispatcher = Dispatcher()
        registry = SceneRegistry(dispatcher)
        registry.add(
            DefaultScene,
            StartAppScene,
            InteractScene,
            FinishScene,
        )
        self.dispatcher = dispatcher

    def send_message_to_channel(self, message):
        with self.channel_lock:
            self.channel_queue.put("text_message:"+message)

    def send_img_to_channel(self, file_path):
        with self.channel_lock:
            self.channel_queue.put("img_message:"+file_path)

    def set_prompt(self, prompt: TelegramPrompt):
        self.prompt = prompt

    def get_prompt(self) -> TelegramPrompt:
        return self.prompt

    def is_prompt_solved(self):
        return self.prompt.is_solved()

    async def _check_new_channel_msgs(self):
        while not self.force_quit:
            msg_type = None
            msg_txt = None
            with self.channel_lock:
                if self.channel_queue.qsize() > 0:
                    message = self.channel_queue.get().split(":")
                    msg_type = message[0]
                    msg_txt = message[1]
            if msg_type is not None:
                if "text_message" == msg_type:
                    await self.bot.send_message(self.channel_id, msg_txt)
                elif "img_message" == msg_type:
                    file_path = msg_txt
                    from aiogram.types import FSInputFile
                    photo = FSInputFile(file_path)
                    await self.bot.send_photo(self.channel_id, photo)
                else:
                    self.logger.debug(f"Failed to send msg to channel {msg_type} {msg_txt}")
            await asyncio.sleep(10)

    async def _listen_telegram_msgs(self):
        await self.dispatcher.start_polling(self.bot)

    async def _thread_async_main(self):
        task1 = asyncio.create_task(self._listen_telegram_msgs())
        task2 = asyncio.create_task(self._check_new_channel_msgs())
        await asyncio.gather(task1, task2)

    def _start(self):
        asyncio.run(self._thread_async_main())

    def start(self):
        if not self.started:
            self.service_thread = Thread(target=self._start, daemon=True)
            self.service_thread.start()
            self.started = True


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    from dotenv import load_dotenv
    load_dotenv()

    img = './tmp/ViewState_29bf105d5f40cb085f6ff7a6438ae6c3_Snapshot.png'
    service = TelegramService()
    service2 = TelegramService()
    print(service2 == service)
    service.start()
    count = 0
    while True:
        service.send_message_to_channel(f"TelegramService started {count}")
        service.send_img_to_channel(img)
        count = count + 1

        quit = input("Quit?")
        if 'y' == quit:
            break

