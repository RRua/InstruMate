import hashlib
import re

from pymate.common.app import App
from pymate.common.command import Command
from pymate.device_link.device_link import DeviceLink
from pymate.device_observer.device_observer import DeviceObserver, DeviceState


class LogCatObserver(DeviceObserver):

    def __init__(self):
        super().__init__("logcat_observer")
        self.command = None

    def configure(self, target_app: str, device_link: DeviceLink, tmp_dir: str = None, output_dir: str = None,
                  tools_dir: str = None,
                  force_overwrite=False,
                  append_to_existing=False):

        super().configure(target_app=target_app, device_link=device_link, tmp_dir=tmp_dir, output_dir=output_dir,
                          tools_dir=tools_dir, force_overwrite=force_overwrite,
                          append_to_existing=append_to_existing)

    def start(self):
        uid = None
        pkg_name = self.get_target_app().get_package_name() if self.get_target_app() is not None and self.get_target_app().get_package_name() is not None else None
        if pkg_name is not None:
            if pkg_name in self.device_link.get_installed_apps():
                uid = self.device_link.get_package_uid(package=pkg_name)
            else:
                raise RuntimeError(f"App is not installed and can't be monitored {pkg_name}")
        cmd_list = ["adb", "-s", self.device_link.androidSerial, "logcat", f"--uid={uid}"] if uid is not None else [
            "adb", "-s", self.device_link.androidSerial, "logcat"]
        self.command = Command(cmd=cmd_list, use_in_memory_output_capturer=True)
        self.command.run(timeout=-1, block=False)

    def discard(self):
        if self.command is not None:
            self.command.kill()

    def do_observe(self) -> DeviceState:
        stdout, stderr = self.command.collect_outputs()
        return LogcatState(stdout, stderr)


class LogcatState(DeviceState):
    def __init__(self, stdout, stderr):
        super().__init__()
        self.state_dict["stdout"] = stdout
        self.state_dict["stderr"] = stderr
        self.log_pattern = re.compile(
            r'(?P<month>\d{1,2})-+(?P<day>\d{1,2})\s+(?P<time>\d{1,2}:\d{1,2}:\d+\.\d+)\s+(?P<pid>\d+)\s+(?P<tid>\d+)\s+(?P<level>[a-zA-Z])\s+(?P<pkg_name>[^\s:]+):+\s+(?P<msg>.*$)')
        self.exception_pattern = re.compile(r'\b[A-Za-z0-9_]+\.(?:[A-Za-z0-9_]+\.)*[A-Za-z0-9_]*Exception\b')
        self.error_pattern = re.compile(r'\b[A-Za-z0-9_]+\.(?:[A-Za-z0-9_]+\.)*[A-Za-z0-9_]*Error\b')
        self.method_signature_pattern = re.compile(r'\b[A-Za-z0-9_]+\.(?:[A-Za-z0-9_]+\.)*[A-Za-z0-9_]*\(.*\)')
        self.method_signature_detail_pattern = re.compile(r'(?P<method_signature>[A-Za-z0-9_\.]*)\((?P<detail>.*)\)')
        self.exception_site_pattern = re.compile(r'\bat\b')
        self.state_dict["parsed_msgs"] = []
        self.state_dict["not_parsed_msgs"] = []
        self.state_dict["level_stats"] = {}
        self.state_dict["pkg_names"] = []
        self._process_output(stdout)
        self._process_output(stderr)
        exceptions_collector = set()
        self._find_exceptions(stdout, exceptions_collector)
        self._find_exceptions(stderr, exceptions_collector)
        self.state_dict["exceptions"] = sorted(exceptions_collector)
        exception_origins = []
        self._find_exception_origins(stdout, self.state_dict["exceptions"], exception_origins)
        self._find_exception_origins(stderr, self.state_dict["exceptions"], exception_origins)
        self.state_dict["exception_origins"] = exception_origins
        result = ";".join(self.state_dict["exceptions"])
        self.state_dict["signature"] = hashlib.md5(result.encode()).hexdigest()

    def _process_output(self, output):
        for string in output:
            match = self.log_pattern.match(string)
            if match:
                group_dict = match.groupdict()
                self.state_dict["parsed_msgs"].append(group_dict)
                level = group_dict["level"]
                pkg_name = group_dict["pkg_name"]
                if level not in self.state_dict["level_stats"]:
                    self.state_dict["level_stats"][level] = 1
                else:
                    self.state_dict["level_stats"][level] = self.state_dict["level_stats"][level] + 1
                if pkg_name not in self.state_dict["pkg_names"]:
                    self.state_dict["pkg_names"].append(pkg_name)
            else:
                self.state_dict["not_parsed_msgs"].append(string)

    def _find_exceptions(self, output, set_collector: set = None):
        for line in output:
            matches = re.findall(self.exception_pattern, line)
            for item in matches:
                set_collector.add(item)
            matches = re.findall(self.error_pattern, line)
            for item in matches:
                set_collector.add(item)

    def _find_exception_origins(self, log_messages, exceptions, collector: list):
        i = 0
        while i < len(log_messages):
            line = log_messages[i]
            for exception_name in exceptions:
                if exception_name in line:
                    w = i + 1
                    while w < len(log_messages) and re.search(self.exception_site_pattern, log_messages[w]):
                        raw_info = log_messages[w]
                        matches = re.findall(self.method_signature_pattern, raw_info)
                        for item in matches:
                            match = re.match(self.method_signature_detail_pattern, item)
                            if match:
                                method_signature = match.group("method_signature")
                                detail = match.group("detail")
                                collector.append({
                                    "exception_name": exception_name,
                                    "method_signature": method_signature,
                                    "detail": detail,
                                    "index": w - i - 1,
                                    "raw_msg": raw_info
                                })
                        w += 1

            i += 1


def main():
    device_link = DeviceLink()
    device_link.configure_device(serialno=None)
    app = App(apk_base_path=".\\input\\apk\\random\\reference-app.apk")
    app.set_package_name("com.forensicmate.referenceapp")
    logcat_observer = LogCatObserver()
    logcat_observer.configure(target_app=app.get_package_name(), device_link=device_link)
    logcat_observer.start()
    import time
    # for i in range(3):
    #     print("sleeping 10 seconds")
    #     time.sleep(10)
    #     stdout, stderr = logcat_observer.command.collect_outputs()
    #     print(f"collected {len(stdout)} stdout lines and {len(stderr)} stderr lines")
    #     for line in stdout:
    #         print(line)
    print(f"killing...")
    logcat_observer.observe()
    time.sleep(30)
    logcat_observer.discard()
    print("killed?")
    time.sleep(10)


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG)
    main()
