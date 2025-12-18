from datetime import datetime
from .StateObserver import StateObserver
from .StateItem import StateItem
from pymate.device_link import DeviceLink
from pymate.utils.utils import write_dict_as_json, diff_values
import hashlib


class EnvironmentObserver(StateObserver):
    def __init__(self, device_link: DeviceLink):
        self.device_link = device_link
        self.last_state = None
        self.current_state = None

    def observe(self):
        self.last_state = self.current_state
        top_activity = self.device_link.get_top_activity_name()
        task_activities = self.device_link.get_task_activities()
        activity_stack = self.device_link.get_current_activity_stack()
        running_services = self.device_link.get_current_running_service_names()
        env_state = EnvironmentStateItem(top_activity, task_activities, activity_stack, running_services)
        self.current_state = env_state

    def has_changed(self):
        if self.last_state is None or self.last_state.is_different(self.current_state):
            return True

    def get_state(self):
        return self.current_state

    def get_last_state(self):
        return self.last_state

    def save_2_folder(self, folder):
        write_dict_as_json(self.current_state.to_dict(), folder,
                           "EnvState_%s.json" % self.current_state.get_signature())
        if self.last_state is not None and self.has_changed():
            differences = self.current_state.get_differences(self.last_state)
            write_dict_as_json(differences, folder, "EnvState_%s_from_%s_Differences.json" % (
                self.current_state.get_signature(), self.last_state.get_signature()))


class EnvironmentStateItem(StateItem):
    def __init__(self, top_activity, task_activities, activity_stack, running_services):
        self.time_tag = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.top_activity = top_activity
        self.task_activities = task_activities
        self.activity_stack = activity_stack
        self.running_services = running_services
        signature_str = (f"{self.top_activity}")
        hash_object = hashlib.md5(signature_str.encode())
        md5_hash = hash_object.hexdigest()
        self.signature = md5_hash

    def get_time_tag(self):
        return self.time_tag

    def to_dict(self):
        state_dict = {
            "time_tag": self.time_tag,
            "signature": self.signature,
            "top_activity": self.top_activity,
            "task_activities": self.task_activities,
            "activity_stack": self.activity_stack,
            "running_services": self.running_services
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
        diff_state_dict = {
            "top_activity": diff_values(other_dict["top_activity"], self_dict["top_activity"]),
            "task_activities": diff_values(other_dict["task_activities"], self_dict["task_activities"]),
            "activity_stack": diff_values(other_dict["activity_stack"], self_dict["activity_stack"]),
            "running_services": diff_values(other_dict["running_services"], self_dict["running_services"]),
        }
        return diff_state_dict
