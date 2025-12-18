from collections import deque
from ActionPolicy import ActionPolicy
from pymate import GraphManager
from pymate.action_manager.ActionMemory import MemoryManager
from pymate.action_manager.ActionPolicy import PolicyInfo
from pymate.action_manager.graph.Action import ActionBag


class BFSPolicy(ActionPolicy):
    def __init__(self, task):
        super().__init__(task)
        self.white_nodes = []
        self.gray_nodes = []
        self.black_nodes = []
        self.node_actions = {}
        self.queue = deque()

    def to_dict(self) -> dict:
        node_actions_dict = {key: action_bag.to_dict() for key, action_bag in self.node_actions.items()}
        return {
            "white_nodes": self.white_nodes,
            "gray_nodes": self.gray_nodes,
            "black_nodes": self.black_nodes,
            "node_actions": node_actions_dict
        }

    @staticmethod
    def from_dict(self, data: dict):
        bfs = BFSPolicy()
        bfs.white_nodes = data["white_nodes"]
        bfs.gray_nodes = data["gray_nodes"]
        bfs.black_nodes = data["black_nodes"]
        bfs.node_actions = {key: ActionBag.from_dict(value) for key, value in data["node_actions"]}
        return bfs


    def can_explore_state(self, state_id):
        return True

    def explore_state(self, state_id):
        # find and build action bag
        # no actions?
        # turn black
        # dequeu gray
        # transition to gray
        pass

    def choose_actions(self, task: str, memory_manager: MemoryManager, graph_manager: GraphManager) -> tuple[
            ActionBag, PolicyInfo]:
        current_state = graph_manager.get_current_state_id()
        if current_state in self.white_nodes:
            return self.explore_state(current_state)
        if current_state in self.gray_nodes:
            if len(self.white_nodes) > 0:

            # there is white node and gray is queued
            # transition to white node
            # there is no white node, make this node white, dequeue and explore
            pass
        if current_state in self.black_nodes:
            # there is white? move to it
            # there is no white, but gray exists, dequeue and move to it
            # all black, finished
            pass
        if current_state not in self.white_nodes and current_state not in self.gray_nodes and not current_state in self.black_nodes:
            # turn state to gray
            # there is white? move to it
            # there is no white, but gray exists, dequeue and move to gray
            # no back, explore this
            pass