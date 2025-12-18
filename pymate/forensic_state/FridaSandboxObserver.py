from .StateItem import StateItem
from .StateObserver import StateObserver
from pymate.frida_sandbox import FridaConnection
from pymate.frida_sandbox import SensitiveApisCollector
from pymate.frida_sandbox import DetailedSandboxCollector
from pymate.frida_sandbox import LoadedModulesCollector
from pymate.frida_sandbox import SandboxStateCollector
from pymate.utils.utils import diff_values, write_dict_as_json, write_array_as_csv
import time
import hashlib
from datetime import datetime

MAX_SANDBOX_WAIT_TIMEOUT_SECS = 20
MIN_SANDBOX_READ_INTERVAL = 5


class FridaSandboxObserver(StateObserver):
    def __init__(self, frida_connection: FridaConnection):
        self.frida_connection = frida_connection
        self.sensitive_apis_collector = self.frida_connection.get_message_handler(SensitiveApisCollector)
        self.loaded_modules_collector = self.frida_connection.get_message_handler(LoadedModulesCollector)
        self.detailed_sandbox_collector = self.frida_connection.get_message_handler(DetailedSandboxCollector)
        self.sandbox_state_collector = self.frida_connection.get_message_handler(SandboxStateCollector)
        self.observed_loaded_classes = 0
        self.observed_loaded_modules = 0
        self.current_state = None
        self.last_state = None

    def observe(self):
        self.last_state = self.current_state
        start_time = time.time()
        while True:
            tmp_observed_loaded_classes = self.sandbox_state_collector.get_observed_loaded_classes()
            tmp_observed_loaded_modules = self.sandbox_state_collector.get_observed_loaded_modules()
            elapsed_time = time.time() - start_time
            has_enumeration_happened = tmp_observed_loaded_classes - self.observed_loaded_classes > 0 and tmp_observed_loaded_modules - self.observed_loaded_modules > 0
            if has_enumeration_happened and elapsed_time> MIN_SANDBOX_READ_INTERVAL:
                sensitive_apis_set = self.sensitive_apis_collector.collect()
                modules_dict = self.loaded_modules_collector.collect()
                detailed_log = self.detailed_sandbox_collector.collect()
                observed_state = FridaSandboxState(sensitive_apis_set=sensitive_apis_set, modules_dict=modules_dict,
                                                   detailed_log=detailed_log)
                self.current_state = observed_state
                break
            else:
                time.sleep(1)

            if elapsed_time > MAX_SANDBOX_WAIT_TIMEOUT_SECS:
                observed_state = self.last_state
                self.current_state = observed_state
                break

    def has_changed(self):
        if self.last_state is None or self.last_state.is_different(self.current_state):
            return True

    def get_state(self):
        return self.current_state

    def get_last_state(self):
        return self.last_state

    def save_2_folder(self, folder):
        write_dict_as_json(self.current_state.to_dict(), folder,
                           "FridaSandboxState_%s.json" % self.current_state.get_signature())
        detailed_log_array = self.current_state.get_detailed_log()
        write_array_as_csv(detailed_log_array, folder,
                           "FridaSandboxState_%s_DetailedLog.csv" % self.current_state.get_signature())
        if self.last_state is not None and self.has_changed():
            differences = self.current_state.get_differences(self.last_state)
            write_dict_as_json(differences, folder, "FridaSandboxState_%s_from_%s_Differences.json" % (
                self.current_state.get_signature(), self.last_state.get_signature()))


class FridaSandboxState(StateItem):
    def __init__(self, sensitive_apis_set, modules_dict, detailed_log):
        self.time_tag = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.sensitive_apis_set = sensitive_apis_set
        self.modules_dict = modules_dict
        self.detailed_log = detailed_log
        sig_as_string = ';'.join(item for item in self.sensitive_apis_set)
        for key in self.modules_dict:
            module_as_string = ';'.join(item for item in self.modules_dict[key])
            sig_as_string = sig_as_string + '--' + module_as_string
        hash_object = hashlib.md5(sig_as_string.encode())
        md5_hash = hash_object.hexdigest()
        self.signature = md5_hash

    def get_time_tag(self):
        return self.time_tag

    def to_dict(self):
        modules = {
            "class_module": list(self.modules_dict["class_module"]),
            "native_module": list(self.modules_dict["native_module"])
        }
        state_dict = {
            "sensitive_apis": list(self.sensitive_apis_set),
            "modules": modules
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
        self_dict = self.to_dict()
        other_dict = other.to_dict()
        modules_diff = {
            "class_module": diff_values(other_dict["modules"]["class_module"], self_dict["modules"]["class_module"]),
            "native_module": diff_values(other_dict["modules"]["native_module"], self_dict["modules"]["native_module"])
        }
        diff_state_dict = {
            "sensitive_apis": diff_values(other_dict["sensitive_apis"], self_dict["sensitive_apis"]),
            "modules": modules_diff,
        }
        return diff_state_dict

    def get_detailed_log(self):
        return self.detailed_log
