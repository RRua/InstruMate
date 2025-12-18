from pymate.action_manager.ActionPolicy import ActionPolicy
from pymate.action_manager.telegram_policy.TelegramService import TelegramService
from pymate.action_manager.telegram_policy.TelegramPrompt import TelegramPrompt
from pymate.action_manager.graph.GraphManager import GraphManager
from pymate.action_manager.ActionMemory import MemoryManager
from pymate.action_manager.graph.Action import ActionBag
import time


class TelegramActionPolicy(ActionPolicy):
    def __init__(self):
        super().__init__()
        self.telegram_service = TelegramService()
        self.telegram_service.start()
        self.succeeded = False

    def choose_actions(self, task: str, memory_manager: MemoryManager, graph_manager: GraphManager ) -> ActionBag:
        prompt = TelegramPrompt(task, graph_manager)
        self.telegram_service.set_prompt(prompt)
        while True:
            if self.telegram_service.is_prompt_solved():
                self.succeeded = True
                return prompt.action_bag
            else:
                time.sleep(3)

    def has_succeeded(self):
        return self.succeeded

    def to_dict(self):
        return {
            "succeeded": self.succeeded
        }
