from .StateObserver import StateObserver
from pymate.device_link import DeviceLink, DirectShell
from pymate.utils.utils import diff_values, write_dict_as_json
from .StateItem import StateItem
from datetime import datetime
import hashlib

IGNORED_FILES = ["/sdcard/window_dump.xml"]

class FileSystemStateObserver(StateObserver):
    def __init__(self, app_private_dir, shared_dir, device_link: DeviceLink):
        self.app_private_dir = app_private_dir
        self.shared_dir = shared_dir
        self.device_link = device_link
        self.ip_addr = device_link.get_wlan_ip_address()
        if self.ip_addr is None:
            raise RuntimeError(
                "Device must be connected to wifi and the direct shell must be running with root privileges")
        self.direct_shell = DirectShell(device_link=device_link, ip_addr=self.ip_addr, use_device_ip_addr=False)
        self.direct_shell.connect()
        self.last_state = None
        self.current_state = None

    def observe(self):
        self.last_state = self.current_state
        if self.last_state is None:
            private_dir_since_ts = -1
            shared_dir_since_ts = -1
        else:
            private_dir_since_ts = self.last_state.get_most_recent_priv_dir_ts()
            shared_dir_since_ts = self.last_state.get_most_recent_shared_dir_ts()

        modifications_priv_dir = self.direct_shell.list_modifications(self.app_private_dir)
        modifications_shared_folder = self.direct_shell.list_modifications(self.shared_dir)
        filtered_modifications_priv_dir = FileSystemStateItem.filter_modifications(modifications_priv_dir,
                                                                                   private_dir_since_ts)
        filtered_modifications_shared_folder = FileSystemStateItem.filter_modifications(modifications_shared_folder,
                                                                                        shared_dir_since_ts)
        observed_state = FileSystemStateItem(filtered_modifications_priv_dir, filtered_modifications_shared_folder)
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
                           "FileSystemState_%s.json" % self.current_state.get_signature())
        self.direct_shell.create_tar("/data/local/tmp/snapshot.tar", self.current_state.get_files())
        self.device_link.adb_pull("/data/local/tmp/snapshot.tar", folder,
                                  "FileSystemState_%s.tar" % self.current_state.get_signature())
        if self.last_state is not None and self.has_changed():
            differences = self.current_state.get_differences(self.last_state)
            write_dict_as_json(differences, folder, "FileSystemState_%s_from_%s_Differences.json" % (
                self.current_state.get_signature(), self.last_state.get_signature()))


class FileSystemStateItem(StateItem):
    def __init__(self, private_dir_modifications, shared_dir_modifications):
        self.time_tag = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.private_dir_modifications = private_dir_modifications
        self.shared_dir_modifications = shared_dir_modifications
        private_dir_signature = ' '.join([d['file'] for d in self.private_dir_modifications["list"]])
        shared_dir_signature = ' '.join([d['file'] for d in self.shared_dir_modifications["list"]])
        signature_str = private_dir_signature + ' ' + shared_dir_signature
        hash_object = hashlib.md5(signature_str.encode())
        md5_hash = hash_object.hexdigest()
        self.signature = md5_hash

    def get_most_recent_priv_dir_ts(self):
        return self.private_dir_modifications["most_recent"]["timestamp"]

    def get_most_recent_shared_dir_ts(self):
        return self.shared_dir_modifications["most_recent"]["timestamp"]

    def get_files(self):
        private_dir_files = [d['file'] for d in self.private_dir_modifications["list"]]
        shared_dir_files = [d['file'] for d in self.shared_dir_modifications["list"]]
        return private_dir_files + shared_dir_files

    @staticmethod
    def filter_modifications(modifications, greater_then_ts=-1):
        filtered = []
        greatest_ts = None
        greatest_ts_str = None
        greatest_file = None
        oldest_ts = None
        oldest_ts_str = None
        oldest_file = None
        for item in modifications:
            if item in IGNORED_FILES:
                continue
            timestamp = item["timestamp"]
            timestamp_fmt = item["timestamp_fmt"]
            file = item["file"]
            if timestamp > greater_then_ts:
                filtered.append(item)
            if greatest_ts is None:
                greatest_ts = timestamp
                greatest_ts_str = timestamp_fmt
                greatest_file = file
            else:
                if timestamp > greatest_ts:
                    greatest_ts = timestamp
                    greatest_ts_str = timestamp_fmt
                    greatest_file = file
            if oldest_ts is None:
                oldest_ts = timestamp
                oldest_ts_str = timestamp_fmt
                oldest_file = file
            else:
                if timestamp < oldest_ts:
                    oldest_ts = timestamp
                    oldest_ts_str = timestamp_fmt
                    oldest_file = file
        most_recent = {
            "timestamp": greatest_ts,
            "timestamp_str": greatest_ts_str,
            "file": greatest_file
        }
        oldest = {
            "timestamp": oldest_ts,
            "timestamp_str": oldest_ts_str,
            "file": oldest_file
        }
        return {
            "most_recent": most_recent,
            "oldest": oldest,
            "list": filtered
        }

    def get_time_tag(self):
        return self.time_tag

    def to_dict(self):
        state_dict = {
            "private_dir": self.private_dir_modifications,
            "shared_dir": self.shared_dir_modifications,
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
        assert isinstance(other, FileSystemStateItem)
        self_dict = self.to_dict()
        other_dict = other.to_dict()
        self_priv_dir_files = [d['file'] for d in self.private_dir_modifications["list"]]
        self_shared_dir_files = [d['file'] for d in self.shared_dir_modifications["list"]]
        other_priv_dir_files = [d['file'] for d in other.private_dir_modifications["list"]]
        other_shared_dir_files = [d['file'] for d in other.shared_dir_modifications["list"]]
        diff_state_dict = {
            "private_dir": diff_values(self_priv_dir_files, other_priv_dir_files),
            "shared_dir": diff_values(self_shared_dir_files, other_shared_dir_files),
        }
        return diff_state_dict
