from datetime import datetime
from pymate.action_manager.graph.Action import ActionBag
from pymate.utils.utils import write_dict_as_json, read_json_as_dict
from abc import abstractmethod
import os
import re


class ActionMemory:

    def __init__(self, state_signature: str, snapshot: str, task: str, action_bag: ActionBag):
        self.state_signature = state_signature
        self.snapshot = snapshot
        self.action_bag = action_bag
        self.task = task
        self.time_tag = datetime.now().strftime("%Y-%m-%d_%H%M%S")

    def to_dict(self):
        return {
            "state_signature": self.state_signature,
            "snapshot": self.snapshot,
            "action_bag": self.action_bag.to_dict(),
            "task": self.task,
            "time_tag": self.time_tag,
        }

    @abstractmethod
    def from_dict(data):
        action_bag = ActionBag.from_dict(data["action_bag"])
        action_memory = ActionMemory(state_signature=data["state_signature"], snapshot=data["snapshot"],
                                     task=data["task"], action_bag=action_bag)
        action_memory.time_tag = data["time_tag"]
        return action_memory

    def save_2_folder(self, folder):
        write_dict_as_json(self.to_dict(), folder,
                           "ActionMemory_%s_at_%s.json" % (self.state_signature, self.time_tag))


class MemoryManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MemoryManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, memory_dir: str, load_past_memories = True):
        if not hasattr(self, 'initialized'):
            import logging
            self.logger = logging.getLogger(self.__class__.__name__)
            self.initialized = True
            self.history_index = {}
            self.history_stack = []
            self.memory_dir = memory_dir
            if load_past_memories:
                self._load_history_from_dir()

    def get_state_history(self, signature)->list:
        if signature in self.history_index:
            return self.history_index[signature]
        else:
            self.history_index[signature] = []
            return self.history_index[signature]

    def _load_history_from_dir(self):
        files = sorted(os.listdir(self.memory_dir))
        for file_name in files:
            pattern = r'ActionMemory_(.*)_at_(.*)\.json'
            match = re.match(pattern, file_name)
            if not match:
                return None
            signature = match.group(1)
            time_tag = match.group(2)
            self.logger.debug(f"Loaded memory {signature} with time tag {time_tag} ")
            memory_dict = read_json_as_dict(file_name=file_name, base_dir=self.memory_dir)
            memory = ActionMemory.from_dict(data=memory_dict)
            self.history_stack.append(memory)
            self.get_state_history(signature).append(memory)

    def add_memory(self, task: str, state_signature: str, state_snapshot: str, action_bag: ActionBag):
        action_memory = ActionMemory(state_signature=state_signature,
                                     snapshot=state_snapshot,
                                     task=task,
                                     action_bag=action_bag)
        self.history_stack.append(action_memory)
        self.get_state_history(action_memory.state_signature).append(action_memory)
        action_memory.save_2_folder(self.memory_dir)

