from .StateObserver import StateObserver
from .StateItem import StateItem
from .EnvironmentObserver import EnvironmentObserver
from datetime import datetime
from pymate.utils.utils import write_dict_as_json
import hashlib


class MultipleStateObserver(StateObserver):
    def __init__(self, *state_observers: StateObserver):
        self.last_state = None
        self.current_state = None
        self.state_observers = []
        for state_observer in state_observers:
            self.state_observers.append(state_observer)

    def observe(self):
        self.last_state = self.current_state
        for state_observer in self.state_observers:
            state_observer.observe()
        multi_state = {}
        signature_str = ""
        for state_observer in self.state_observers:
            class_name = state_observer.__class__.__name__
            state = state_observer.get_state()
            multi_state[class_name] = state
            signature_str += state.get_signature()
        hash_object = hashlib.md5(signature_str.encode())
        md5_hash = hash_object.hexdigest()
        multi_state["signature"] = md5_hash
        self.current_state = MultipleStateItem(multi_state)

    def has_changed(self):
        for state_observer in self.state_observers:
            if state_observer.has_changed():
                return True
        return False

    def get_state(self):
        return self.current_state

    def get_last_state(self):
        return self.last_state

    def save_2_folder(self, folder):
        for state_observer in self.state_observers:
            state_observer.save_2_folder(folder)
        write_dict_as_json(self.current_state.to_dict(), folder,
                           "MultipleState_%s.json" % self.current_state.get_signature())


class MultipleStateItem(StateItem):
    def __init__(self, multi_state_dict):
        self.time_tag = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.multi_state_dict = multi_state_dict

    def get_time_tag(self):
        return self.time_tag

    def to_dict(self):
        state_dict = {}
        for key in self.multi_state_dict:
            value = self.multi_state_dict[key]
            if isinstance(value, StateItem):
                state_dict[key] = value.get_signature()
            else:
                state_dict[key] = value
        return state_dict

    def get_signature(self):
        return self.multi_state_dict["signature"]

    def is_different(self, other):
        assert other is not None
        assert isinstance(other, StateItem)
        return self.get_signature() != other.get_signature()

    def get_differences(self, other):
        return {}

    def get_state_by_class(self, cls):
        key = cls.__name__
        if key in self.multi_state_dict:
            return self.multi_state_dict[key]
        else:
            return None

