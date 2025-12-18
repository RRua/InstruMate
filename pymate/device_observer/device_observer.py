import logging
import os
import time
from abc import abstractmethod
from datetime import datetime

from pymate.common.app import App
from pymate.device_link.device_link import DeviceLink
from pymate.utils import utils


class DeviceState:

    def __init__(self, signature=None):
        self.state_dict = dict()
        self.state_dict["signature"] = signature
        self.state_dict["time_record"] = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.state_dict["time_record_millis"] = int(time.time() * 1000)

    def set_time_record(self, time_record):
        self.state_dict["time_record"] = time_record

    def get_time_record(self):
        return self.state_dict.get("time_record", None)

    def get_signature(self):
        return self.state_dict.get("signature", None)

    def save(self, dest_dir):
        state_dict = self.to_dict()
        utils.write_dict_as_json(json_dict=state_dict, base_dir=dest_dir, file_name=f"{self.get_signature()}.json",
                                 overwrite_existing=True)

    def to_dict(self):
        return self.state_dict

    def from_dict(self, state_dict):
        self.state_dict = state_dict

    def is_different(self, other):
        if other is None:
            return True
        if self.get_signature() is not None and other.get_signature() is not None:
            return self.get_signature() == other.get_signature()
        raise RuntimeError('Signature must not be none to compare states')

    def get_differences(self, other):
        return utils.diff_dictionaries(self.state_dict, other.state_dict)


class DeviceObserver:

    def __init__(self, name: str = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        if name is not None:
            self.name = name
        else:
            self.name = self.__class__.__name__
        self.target_app = None
        self.device_link: DeviceLink = None
        self.tmp_dir = None
        self.output_dir = None
        self.tools_dir = None
        self.observer_log = None
        self.force_overwrite = None
        self.append_to_existing = None
        self.last_state: DeviceState = None
        self.current_state: DeviceState = None
        self.started = False

    def get_output_dir(self):
        observer_dir = os.path.join(self.output_dir, self.name)
        if not os.path.exists(observer_dir):
            os.makedirs(observer_dir)
        return observer_dir

    def configure(self, target_app: App, device_link: DeviceLink, tmp_dir: str = None, output_dir: str = None,
                  tools_dir: str = None, force_overwrite=False,
                  append_to_existing=False):
        self.target_app: App = target_app
        self.device_link = device_link
        self.tmp_dir = tmp_dir
        self.output_dir = output_dir
        self.tools_dir = tools_dir
        self.force_overwrite = force_overwrite
        self.append_to_existing = append_to_existing

    def start(self):
        pass

    def observe(self) -> DeviceState:
        if self.target_app is not None:
            self.logger.debug(f"Observing app state {self.target_app.get_package_name()}")
        else:
            self.logger.debug(f"Observing device view state. No target app configured.")
        state = self.do_observe()
        return state

    def discard(self):
        pass

    def observe_and_save(self) -> DeviceState:
        if self.target_app is not None:
            self.logger.debug(f"Observing app state {self.target_app.get_package_name()}")
        else:
            self.logger.debug(f"Observing device view state. No target app configured.")
        state = self.observe()
        output_dir = self.get_output_dir()
        if state is not None:
            state.save(output_dir)
        return state

    def save(self, state: DeviceState):
        output_dir = self.get_output_dir()
        if state is not None:
            state.save(output_dir)

    @abstractmethod
    def do_observe(self) -> DeviceState:
        raise NotImplementedError()

    def has_changed(self):
        if self.current_state is None and self.last_state is None:
            return False
        if self.last_state is None and self.current_state is not None:
            return True
        if self.last_state is not None and self.current_state is None:
            raise RuntimeError("Current state is none, but last state was identified. Bug?")
        return self.current_state.is_different(self.last_state)

    def get_state(self):
        return self.current_state

    def get_last_state(self):
        return self.last_state

    def get_target_app(self) -> App:
        return self.target_app
