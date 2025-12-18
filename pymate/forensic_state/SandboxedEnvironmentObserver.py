from .StateObserver import StateObserver
from .StateItem import StateItem
from .FridaSandboxObserver import FridaSandboxObserver, FridaSandboxState
from .EnvironmentObserver import EnvironmentObserver, EnvironmentStateItem
from datetime import datetime
import hashlib
from pymate.utils.utils import write_dict_as_json, write_array_as_csv


class SandboxedEnvironmentObserver(StateObserver):
    def __init__(self, frida_sandbox_observer: FridaSandboxObserver, env_observer: EnvironmentObserver):
        self.frida_sandbox_observer = frida_sandbox_observer
        self.env_observer = env_observer
        self.current_state = None
        self.last_state = None

    def observe(self):
        self.last_state = self.current_state
        self.env_observer.observe()
        if self.env_observer.has_changed():
            self.frida_sandbox_observer.sensitive_apis_collector.set_clear_on_next_collection()
        self.frida_sandbox_observer.observe()
        self.current_state = SandboxedEnvironmentState(env_state=self.env_observer.get_state(),
                                                       frida_state=self.frida_sandbox_observer.get_state())

    def has_changed(self):
        if self.last_state is None or self.last_state.is_different(self.current_state):
            return True

    def get_state(self):
        return self.current_state

    def get_last_state(self):
        return self.last_state

    def save_2_folder(self, folder):
        write_dict_as_json(self.current_state.to_dict(), folder,
                           "SandboxedEnvState_%s.json" % self.current_state.get_signature())
        detailed_log_array = self.current_state.frida_state.get_detailed_log()
        write_array_as_csv(detailed_log_array, folder,
                           "SandboxedEnvState_%s_DetailedLog.csv" % self.current_state.get_signature())
        if self.last_state is not None and self.has_changed():
            differences = self.current_state.get_differences(self.last_state)
            write_dict_as_json(differences, folder, "SandboxedEnvState_%s_from_%s_Differences.json" % (
                self.current_state.get_signature(), self.last_state.get_signature()))


class SandboxedEnvironmentState(StateItem):
    def __init__(self, env_state: EnvironmentStateItem, frida_state: FridaSandboxState):
        self.time_tag = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.env_state = env_state
        self.frida_state = frida_state
        signature_str = self.env_state.get_signature() + '-' + self.frida_state.get_signature()
        hash_object = hashlib.md5(signature_str.encode())
        md5_hash = hash_object.hexdigest()
        self.signature = md5_hash

    def get_time_tag(self):
        return self.time_tag

    def to_dict(self):
        state_dict = {
            "env_state": self.env_state.to_dict(),
            "frida_sandbox_state": self.frida_state.to_dict(),
        }
        return state_dict

    def get_signature(self):
        return self.signature

    def is_different(self, other):
        assert other is not None
        assert isinstance(other, StateItem)
        return self.get_signature() != other.get_signature()

    def get_differences(self, other):
        assert other is not None
        assert isinstance(other, StateItem)
        diff_state_dict = {
            "env_state_diffs": self.env_state.get_differences(other.env_state),
            "frida_sandbox_state_diffs": self.frida_state.get_differences(other.frida_state),
        }
        return diff_state_dict
