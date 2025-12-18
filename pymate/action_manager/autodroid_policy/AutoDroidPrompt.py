import logging
import re
from abc import abstractmethod
from pymate.action_manager.graph.Action import UIAction
from pymate.action_manager.graph.UIActionUnit import ACTION_TYPE_TAP, ACTION_TYPE_INPUT
from pymate.action_manager.graph.GraphManager import GraphManager


class PromptResponse:
    def __init__(self, resp_str):
        assert resp_str is not None
        self.steps_to_complete_task = None
        self.resp_previous_actions = None
        self.is_task_finished = None
        self.can_proceed = None
        self.actions = []
        self.resp_str = resp_str
        patterns = self.get_patterns()
        self.parsed_patterns = PromptResponse._parse_with_regex(patterns, resp_str)
        self.post_regex_process()

    @abstractmethod
    def get_patterns(self):
        raise NotImplementedError()

    @abstractmethod
    def post_regex_process(self):
        raise NotImplementedError()

    @abstractmethod
    def has_actions(self):
        raise NotImplementedError()

    @staticmethod
    def _parse_with_regex(pattern_dict, resp_str):
        patterns = pattern_dict
        values = {}
        resp_lines = resp_str.lower().splitlines()
        for line in resp_lines:
            for key in patterns:
                key_pattern_list = patterns[key]
                for pattern in key_pattern_list:
                    match = re.search(pattern, line)
                    if match:
                        all_groups = match.groups()
                        values[key] = all_groups
                        break
        return values

    @staticmethod
    def parse_bool_resp_str(resp_str):
        is_bool = resp_str == "y" or resp_str == "yes"
        is_not_bool = resp_str == "n" or resp_str == "no"
        if is_bool == is_not_bool:
            return None
        else:
            return is_bool


class Prompt:
    def __init__(self, task: str):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.task = task

    def get_prompt_str(self):
        context = self.get_prompt_context()
        previous_actions = self.get_previous_actions_str()
        current_ui_actions = self.get_current_ui_actions_str()
        question = self.get_question_str()
        return f"{context}\n" \
               f"{previous_actions}\n" \
               f"{current_ui_actions}\n" \
               f"{question}"

    @abstractmethod
    def get_prompt_context(self):
        raise NotImplementedError()

    @abstractmethod
    def get_previous_actions_str(self):
        raise NotImplementedError()

    @abstractmethod
    def get_current_ui_actions_str(self):
        raise NotImplementedError()

    @abstractmethod
    def get_question_str(self):
        raise NotImplementedError()

    @abstractmethod
    def parse_question_response(self, resp):
        raise NotImplementedError()

    @abstractmethod
    def get_prompt_response(self) -> PromptResponse:
        raise NotImplementedError

    def get_simplified_html_for_action(self, action: UIAction):
        action_unit = action.action_unit
        if ACTION_TYPE_TAP == action_unit.action_type:
            if action.executed:
                return f"- TapOn: <button id='{action_unit.view_id}'>{action_unit.label}</button>"
            else:
                return f"<button id='{action_unit.view_id}'>{action_unit.label}</button>"
        elif ACTION_TYPE_INPUT == action_unit.action_type:
            if action.executed:
                return f"- TapOn: <input id='{action_unit.view_id}'>{action_unit.label}</input> InputText: {action.text}"
            else:
                return f"<input id='{action_unit.view_id}'>{action_unit.label}</input>"
        else:
            raise NotImplementedError


class AutoDroidPromptResponse(PromptResponse):

    def __init__(self, resp_str):
        super().__init__(resp_str)

    def get_patterns(self):
        return {
            "steps": ['.*c.*task.*steps:(.*)\\.'],
            "previous_actions": ['.*analyses.*previous.*actions.*:(.*)\.*'],
            "is_finished": ['.*is the task.*finished\?\s(\w+)\.+\s(.*)'],
            "can_proceed": ['.*can.*proceed.*\?\s(\w+)\.*'],
            "next_interaction": ['.*next.*interaction:[\s-]*id=([\w/]*)[\s-]*action=([\w]*)[\s-]*input text=([\w]*)\.*']
        }

    def post_regex_process(self):
        self._parse_steps_to_complete_task()
        self._parse_resp_previous_actions()
        self._parse_is_task_finished()
        self._parse_can_proceed()
        self._parse_get_interaction()

    def _parse_steps_to_complete_task(self):
        if self.parsed_patterns is not None and "steps" in self.parsed_patterns:
            self.steps_to_complete_task = self.parsed_patterns["steps"]

    def _parse_resp_previous_actions(self):
        if self.parsed_patterns is not None and "previous_actions" in self.parsed_patterns:
            self.resp_previous_actions = self.parsed_patterns["previous_actions"]

    def _parse_is_task_finished(self):
        if self.parsed_patterns is not None and "is_finished" in self.parsed_patterns:
            is_finished_group = self.parsed_patterns["is_finished"]
            if len(is_finished_group) > 0:
                is_finished_str = is_finished_group[0]
                is_finished_bool = PromptResponse.parse_bool_resp_str(is_finished_str)
                self.is_task_finished = is_finished_bool

    def _parse_can_proceed(self):
        if self.parsed_patterns is not None and "can_proceed" in self.parsed_patterns:
            can_proceed_group = self.parsed_patterns["can_proceed"]
            if len(can_proceed_group) > 0:
                is_str = can_proceed_group[0]
                is_bool = PromptResponse.parse_bool_resp_str(is_str)
                self.can_proceed = is_bool

    def _parse_get_interaction(self):
        if self.parsed_patterns is not None and "next_interaction" in self.parsed_patterns:
            next_interaction_group = self.parsed_patterns["next_interaction"]
            if len(next_interaction_group) == 3:
                view_id = next_interaction_group[0]
                action = next_interaction_group[1]
                input_text = next_interaction_group[2]
                action = {
                    "view_id": view_id,
                    "action": action,
                    "input_text": input_text
                }
                self.actions = [action]

    def has_actions(self):
        if self.actions is not None and len(self.actions) > 0:
            return True
        return False


class AutoDroidPrompt(Prompt):
    def __init__(self, task: str, graph_manager: GraphManager):
        super().__init__(task=task)
        self.action_bag = graph_manager.get_current_state_action_bag()
        # TODO re-implement history?
        self.history = []
        self.autodroid_prompt_response = None

    def get_prompt_context(self):
        prompt_context = f"You are a smartphone assistant to help users complete tasks by " \
                         f"interacting with mobile apps.Given a task, the previous UI actions, " \
                         f"and the content of current UI state, your job is to decide whether the " \
                         f"task is already finished by the previous actions, and if not, decide " \
                         f"which UI element in current UI state should be interacted. \n" \
                         f"Task: {self.task}"
        return prompt_context

    def get_previous_actions_str(self):
        if len(self.history) == 0:
            return ''
        result = "Previous UI actions:\n"
        for history_item in self.history:
            actions = history_item.get_actions()
            for action in actions:
                if action.executed and action.success:
                    action_hist_str = self.get_simplified_html_for_action(action)
                    result = result + action_hist_str + "\n"
        return result

    def get_current_ui_actions_str(self):
        result = "Current UI state:\n"
        for action in self.action_bag.actions:
            action_str = self.get_simplified_html_for_action(action)
            result = result + action_str + "\n"
        return result

    def get_question_str(self):
        question = "Your answer should always use the following format:\n" \
                   "1. Completing this task on a smartphone usually involves these steps: <?>.\n" \
                   "2. Analyses of the relations between the task and the previous UI actions and current UI state: <?>.\n" \
                   "3. Based on the previous actions, is the task already finished? <Y/N>. The next step should be <?/None>\n" \
                   "4. Can the task be proceeded with the current UI state? <Y/N>. \n" \
                   "Fill in the blanks about the next one interaction: - id=<view id> - action=<tap/input> - input text=<text or N/A>\n"
        return question

    def parse_question_response(self, resp):
        self.logger.debug(f"Prompt response: {resp}")
        prompt_resp = AutoDroidPromptResponse(resp_str=resp)
        self.autodroid_prompt_response = prompt_resp
        if prompt_resp.has_actions():
            for act in prompt_resp.actions:
                view_id = act["view_id"]
                input_text = act["input_text"]
                for action in self.action_bag.actions:
                    action_unit = action.action_unit
                    if view_id == action_unit.view_id:
                        action.to_be_executed = True
                        action.text = input_text

    def get_prompt_response(self) -> PromptResponse:
        return self.autodroid_prompt_response
