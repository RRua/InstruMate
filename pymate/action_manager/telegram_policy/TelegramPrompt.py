import logging
from pymate.action_manager.graph.GraphManager import GraphManager


class TelegramPrompt:
    def __init__(self, task: str, graph_manager: GraphManager):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.task = task
        self.graph_manager = graph_manager
        self.action_position = 0
        self.solved = False
        self.action_bag = graph_manager.get_current_state_action_bag()

    def get_image(self):
        return self.graph_manager.get_current_state_snapshot()

    def has_next(self):
        return self.action_position < len(self.action_bag.actions) - 1

    def move_next(self):
        if self.has_next():
            self.action_position = self.action_position + 1

    def move_back(self):
        if self.action_position > 0:
            self.action_position = self.action_position - 1

    def get_curr_action(self):
        if self.action_position < len(self.action_bag.actions):
            curr_action = self.action_bag.actions[self.action_position]
            return curr_action
        return None

    def get_action_str(self):
        curr_action = self.get_curr_action()
        if curr_action is not None:
            action_unit = curr_action.action_unit
            curr_unit_str = f"view_id: {action_unit.view_id}\n" \
                            f"label: {action_unit.label}\n" \
                            f"type: {action_unit.action_type}\n" \
                            f"pkg: {action_unit.pkg}\n" \
                            f"cls: {action_unit.cls}\n" \
                            f"to_execute: {curr_action.to_be_executed}\n" \
                            f"input: {curr_action.text}"
            self.logger.debug(curr_unit_str)
            return curr_unit_str
        return None

    def set_action_tap(self):
        curr_action = self.get_curr_action()
        if curr_action is not None:
            curr_action.to_be_executed = True

    def set_auto_input_text(self):
        curr_action = self.get_curr_action()
        if curr_action is not None:
            curr_action.to_be_executed = True
            from pymate.action_manager.input_generator.InputManager import InputManager
            input_manager = InputManager()
            generated_txt = input_manager.get_default_input_generator().generate(curr_action.action_unit)
            curr_action.text = generated_txt
            return generated_txt
        return 'None'

    def set_action_ignore(self):
        curr_action = self.get_curr_action()
        if curr_action is not None:
            curr_action.to_be_executed = False

    def set_input_text(self, text):
        curr_action = self.get_curr_action()
        if curr_action is not None:
            curr_action.to_be_executed = True
            curr_action.text = text

    def set_action_scroll(self, fling_mode):
        curr_action = self.get_curr_action()
        if curr_action is not None:
            curr_action.sub_action = fling_mode
            curr_action.to_be_executed = True

    def is_solved(self):
        return self.solved

    def set_solved(self, solved):
        self.solved = solved

    def set_action_key_back(self):
        self.action_bag.add_key_action_back()

    def set_action_key_home(self):
        self.action_bag.add_key_action_home()

    def set_action_key_enter(self):
        self.action_bag.add_key_action_enter()
