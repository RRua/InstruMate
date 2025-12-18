import hashlib
from .StateObserver import StateObserver
from .StateItem import StateItem
from pymate.device_link import DeviceLink
from pymate.utils.utils import write_dict_as_json, diff_values
from pymate.utils.uiautomator_utils import collect_components, take_snapshot_and_save
from datetime import datetime


class ViewStateObserver(StateObserver):
    def __init__(self, device_link: DeviceLink):
        self.device_link = device_link
        self.last_state = None
        self.current_state = None

    def observe(self):
        views = self.device_link.get_current_view()
        assert views is not None
        self.last_state = self.current_state
        observed_state = ViewStateItem(views)
        self.current_state = observed_state

    def has_changed(self):
        if self.last_state is None or self.last_state.is_different(self.current_state):
            return True

    def get_state(self):
        return self.current_state

    def get_last_state(self):
        return self.last_state

    def save_2_folder(self, folder):
        write_dict_as_json(self.current_state.to_dict(), folder,
                           "ViewState_%s.json" % self.current_state.get_signature())
        take_snapshot_and_save(self.device_link.viewClient, folder,
                               "ViewState_%s_Snapshot.png" % self.current_state.get_signature())
        if self.last_state is not None and self.has_changed():
            differences = self.current_state.get_differences(self.last_state)
            write_dict_as_json(differences, folder, "ViewState_%s_from_%s_Differences.json" % (
                self.current_state.get_signature(), self.last_state.get_signature()))


class ViewStateItem(StateItem):
    def __init__(self, views):
        self.time_tag = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        view_components, by_class_catalog, clickables, checkables, scrollables = collect_components(views)
        signature_set = set()
        for key in view_components:
            signature_set.add(view_components[key]["signature"])
        sorted_sigs = sorted(signature_set)
        result = "\n".join(sorted_sigs)
        hash_object = hashlib.md5(result.encode())
        md5_hash = hash_object.hexdigest()
        self.signature = md5_hash
        self.view_components = view_components
        self.by_class_catalog = by_class_catalog
        self.clickables = clickables
        self.checkables = checkables
        self.scrollables = scrollables

    def get_time_tag(self):
        return self.time_tag

    def to_dict(self):
        state_dict = {
            "time_tag": self.time_tag,
            "signature": self.signature,
            "clickables": self.clickables,
            "checkables": self.checkables,
            "scrollables": self.scrollables,
            "by_class_catalog": self.by_class_catalog,
            "view_components": self.view_components
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
            "view_components": diff_values(other_dict["view_components"], self_dict["view_components"]),
            "clickables": diff_values(other_dict["clickables"], self_dict["clickables"]),
            "checkables": diff_values(other_dict["checkables"], self_dict["checkables"]),
            "scrollables": diff_values(other_dict["scrollables"], self_dict["scrollables"]),
            "by_class_catalog": diff_values(other_dict["by_class_catalog"], self_dict["by_class_catalog"]),
        }
        return diff_state_dict
