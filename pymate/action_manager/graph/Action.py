from abc import abstractmethod
from pymate.action_manager.graph.UIActionUnit import *
from pymate.device_link.device_link import DeviceLink
import logging
from datetime import datetime

KEYCODE_BACK = "KEYCODE_BACK"
KEYCODE_HOME = "KEYCODE_HOME"
KEYCODE_ENTER = "KEYCODE_ENTER"


class Action:

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.executed = False
        self.success = False
        self.to_be_executed = True
        self.execution_timestamp = None
        self.execution_failed = False
        self.failed_message = None

    def _mark_execution_success(self):
        self.executed = True
        self.to_be_executed = False
        self.execution_failed = False
        self.execution_timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")

    def _mark_execution_failure(self, msg: str):
        self.failed_message = msg
        self.executed = True
        self.to_be_executed = False
        self.execution_failed = True
        self.execution_timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.logger.error(msg)

    def is_executed(self):
        return self.executed

    def is_to_be_executed(self):
        return self.to_be_executed

    def has_succeeded(self):
        return self.success

    def to_dict(self):
        return {
            "executed": self.executed,
            "success": self.success,
            "execution_timestamp": self.execution_timestamp
        }

    @abstractmethod
    def execute_action(self, device_link: DeviceLink):
        raise NotImplementedError()


class UIAction(Action):

    def __init__(self, action_unit: UIActionUnit, text: str, sub_action=None):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.action_unit = action_unit
        self.text = text
        self.sub_action = sub_action

    def to_dict(self):
        dict_obj = super().to_dict()
        dict_obj["action_unit"] = self.action_unit.to_dict()
        dict_obj["text"] = self.text
        dict_obj["sub_action"] = self.sub_action
        return dict_obj

    @staticmethod
    def from_dict(data):
        action_unit = UIActionUnit.from_dict(data["action_unit"])
        action = UIAction(action_unit, data["text"], data["sub_action"])
        return action

    def execute_action(self, device_link: DeviceLink):
        if self.to_be_executed:
            view = device_link.viewClient.findViewById(self.action_unit.view_id)
            if view is not None:
                if self.action_unit.action_type == ACTION_TYPE_TAP:
                    view.touch()
                    self._mark_execution_success()
                elif self.action_unit.action_type == ACTION_TYPE_INPUT:
                    view.setText(self.text)
                    self._mark_execution_success()
                elif self.action_unit.action_type == ACTION_TYPE_SCROLL:
                    ui_scrollable = view.uiScrollable
                    if ui_scrollable is not None:
                        if self.sub_action is not None:
                            if SUB_ACTION_SCROLL_FLING_FORWARD == self.sub_action:
                                ui_scrollable.flingForward()
                                self._mark_execution_success()
                            elif SUB_ACTION_SCROLL_FLING_BACKWARD == self.sub_action:
                                ui_scrollable.flingBackward()
                                self._mark_execution_success()
                            elif SUB_ACTION_SCROLL_FLING_TO_START == self.sub_action:
                                ui_scrollable.flingToBeginning()
                                self._mark_execution_success()
                            elif SUB_ACTION_SCROLL_FLING_TO_END == self.sub_action:
                                ui_scrollable.flingToEnd()
                                self._mark_execution_success()
                            else:
                                ui_scrollable.flingForward()
                                self._mark_execution_success()
                        else:
                            ui_scrollable.flingForward()
                            self._mark_execution_success()
                    else:
                        self._mark_execution_failure(
                            f"ACTION cant be taken for view {self.action_unit.view_id}. uiScrollable not found.")
                else:
                    self._mark_execution_failure(
                        f"ACTION cant be taken for view {self.action_unit.view_id}. Neither tap or input.")
            else:
                self._mark_execution_failure(
                    f"ACTION cant be taken for view {self.action_unit.view_id}. View does not exists.")


class KeyAction(Action):

    def __init__(self, key_code):
        super().__init__()
        self.key_code = key_code

    def execute_action(self, device_link: DeviceLink):
        device_link.adb_keyevent(self.key_code)
        self._mark_execution_success()

    def to_dict(self):
        dict_obj = super().to_dict()
        dict_obj["key_code"] = self.key_code
        return dict_obj


class ActionBag:
    def __init__(self):
        self.actions = []
        self.executed = False
        self.executed_success_count = -1
        self.executed_failed_count = -1

    def add_action(self, action: Action):
        self.actions.append(action)

    def add_key_action(self, key_event):
        self.actions.append(KeyAction(key_event))

    def add_key_action_back(self):
        self.actions.append(KeyAction(KEYCODE_BACK))

    def add_key_action_home(self):
        self.actions.append(KeyAction(KEYCODE_HOME))

    def add_key_action_enter(self):
        self.actions.append(KeyAction(KEYCODE_ENTER))

    def has_pending_actions(self):
        for action in self.actions:
            if action.to_be_executed and not action.executed:
                return True
        return False

    def bulk_execute(self, device_link: DeviceLink):
        count = 0
        failed_count = 0
        for action in self.actions:
            if action.is_to_be_executed() and not action.is_executed():
                action.execute(device_link=device_link)
                if action.execution_failed:
                    failed_count = failed_count + 1
                else:
                    count = count + 1
        self.executed_success_count = count
        self.executed_failed_count = failed_count
        self.executed = True

    def to_dict(self):
        actions_dicts = [action.to_dict() for action in self.actions]
        return {
            "executed": self.executed,
            "failed_count": self.executed_failed_count,
            "success_count": self.executed_success_count,
            "actions": actions_dicts,
        }

    @staticmethod
    def from_action_units_dict(action_units):
        action_bag = ActionBag()
        for action_unit_dict in action_units:
            action_unit = UIActionUnit.from_dict(action_unit_dict)
            action_bag.add_action(action_unit)
        return action_bag

    @staticmethod
    def from_dict(data: dict):
        action_bag = ActionBag.from_action_units_dict(data["actions"])
        action_bag.executed = data["executed"]
        action_bag.executed_failed_count = data["failed_count"]
        action_bag.executed_success_count = data["success_count"]
        return action_bag
