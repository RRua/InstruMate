from abc import abstractmethod
from pymate.action_manager.ActionPolicy import ActionPolicy, PolicyInfo
from pymate.action_manager.graph.GraphManager import GraphManager
from pymate.action_manager.ActionMemory import MemoryManager
from pymate.action_manager.graph.Action import ActionBag
import logging

MAX_ERRORS_PER_POLICY = 3
MAX_RETRIES_SAME_STATE = 3


class PolicyStrategy:

    def __init__(self, policies=[]):
        self.policies = policies

    @abstractmethod
    def apply(self, task: str, memory_manager: MemoryManager, graph_manager: GraphManager) -> tuple[
        ActionBag, PolicyInfo]:
        raise NotImplementedError


class MoveNextPolicyStrategy(PolicyStrategy):
    def __init__(self, action_policies=[], max_errors_per_policy=MAX_ERRORS_PER_POLICY,
                 max_retries_on_same_state=MAX_RETRIES_SAME_STATE):
        super().__init__(action_policies)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.max_errors_per_policy = max_errors_per_policy
        self.max_retries_on_same_state = max_retries_on_same_state
        self.policy_err_count = 0
        self.policy_state_id = None
        self.policy_same_state_count = 0
        self.last_state_id = None
        self.current_policy = 0

    def get_current_policy(self) -> ActionPolicy:
        if self.policy_err_count > self.max_errors_per_policy:
            self.next_policy()
        policy = self.policies[self.current_policy]
        return policy

    def next_policy(self):
        self.policy_err_count = 0
        self.policy_same_state_count = 0
        self.current_policy = (self.current_policy + 1) % (len(self.policies))

    def _inc_same_state_count(self):
        self.policy_same_state_count = self.policy_same_state_count + 1
        if self.policy_same_state_count > self.max_retries_on_same_state:
            self.next_policy()

    def apply(self, task: str, memory_manager: MemoryManager, graph_manager: GraphManager) -> tuple[
            ActionBag, PolicyInfo]:
        policy = self.get_current_policy()
        try:
            policy_class_name = policy.__class__.__name__
            state_signature = graph_manager.get_current_state_id()
            self.logger.info(f"Applying policy {policy_class_name} on state {state_signature}")
            action_bag, policy_info = policy.choose_actions(task, memory_manager, graph_manager)
            if state_signature == self.last_state_id:
                self._inc_same_state_count()
            else:
                self.last_state_id = state_signature
            return action_bag, policy_info
        except Exception:
            self.policy_err_count = self.policy_err_count + 1
            import traceback
            traceback.print_exc()
            print(traceback.format_exc())
