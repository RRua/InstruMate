import logging
from pymate.device_link.device_link import DeviceLink
from pymate.forensic_state.MultipleStateObserver import MultipleStateItem
from pymate.action_manager.graph.GraphManager import GraphManager
from pymate.action_manager.policy_strategy.PolicyStrategy import PolicyStrategy
from pymate.action_manager.ActionMemory import MemoryManager


class ActionManager:

    def __init__(self, project_dir: str, memory_dir: str, states_dir: str, task: str, policy_strategy: PolicyStrategy,
                 device_link: DeviceLink):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.device_link = device_link
        self.states_dir = states_dir
        self.memory_dir = memory_dir
        self.project_dir = project_dir
        self.task = task
        self.policy_strategy = policy_strategy
        self.graph_manager = GraphManager(graph_dir=self.project_dir, states_dir=states_dir)
        self.memory_manager = MemoryManager(memory_dir=self.memory_dir, load_past_memories=True)

    def apply_policy_strategy(self) -> dict:
        strategy_class_name = self.policy_strategy.__class__.__name__
        self.logger.info(f"Applying policy strategy {strategy_class_name}")
        action_bag, policy_info = self.policy_strategy.apply(task=self.task, memory_manager=self.memory_manager,
                                                             graph_manager=self.graph_manager)
        bulk_execute = False
        if action_bag.has_pending_actions():
            action_bag.bulk_execute(self.device_link)
            bulk_execute = True
        if bulk_execute or policy_info.success:
            self.memory_manager.add_memory(task=self.task, state_signature=self.graph_manager.get_current_state_id(),
                                           state_snapshot=self.graph_manager.get_current_state_snapshot(),
                                           action_bag=action_bag)
        action_dict = {
            "bulk_execute": bulk_execute,
            "action_bag": action_bag.to_dict(),
            "policy_info": policy_info.to_dict()
        }
        return action_dict
