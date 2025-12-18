import re
import os
import time
import logging
import traceback
from datetime import datetime
import subprocess
from com.dtmilano.android.adb.adbclient import AdbClient
from com.dtmilano.android.viewclient import ViewClient, KEY_EVENT, View, VERSION_SDK_PROPERTY

from pymate.utils.uiautomator_utils import collect_components
from pymate.common.command import Command
from pymate.common import ui_actions

KEYCODE_BACK = "KEYCODE_BACK"
KEYCODE_HOME = "KEYCODE_HOME"
KEYCODE_ENTER = "KEYCODE_ENTER"

DEFAULT_SLEEP = 3

DEFAULT_LOST_CONNECTION_MSG = "Device is not ready. Lost connection. Try recycling the object."


def list_adb_devices():
    logger = logging.getLogger(f"DeviceLink.list_adb_devices")
    result = []
    cmd_list = ["adb", "devices"]
    command = Command(cmd=cmd_list)
    command.run(timeout=-1, block=True)
    stdout, stderr = command.collect_outputs()
    return_code = command.process.returncode
    if stdout is not None and return_code == 0:
        lines = stdout.splitlines()
        if len(lines) == 0:
            raise RuntimeError(f"Error collecting list of devices: {stdout} - {stderr}")
        if lines[0] != 'List of devices attached':
            raise RuntimeError(f"Did adb return the list of connected devices? {stdout} - {stderr}")
        for line in lines:
            if 'device' in line and line != 'List of devices attached':
                device_serial = line.split()[0]
                result.append(device_serial)
        logger.debug(f"Adb devices available {str(result)}")
    return result


def adb_kill_server():
    logger = logging.getLogger(f"DeviceLink.adb_kill_server")
    cmd_list = ["adb", "kill-server"]
    command = Command(cmd=cmd_list)
    command.run(timeout=-1, block=True)
    stdout, stderr = command.collect_outputs()
    return_code = command.process.returncode
    logger.debug(f"adb_kill_server returned {return_code}, stdout: {stdout}, stderr: {stderr}")
    logger.info("adb kill-server")


class AdaptedViewClient(ViewClient):

    def __init__(self, sdk_version):
        self.uiAutomatorHelper = False
        self.device = None
        self.build = {}
        self.build[VERSION_SDK_PROPERTY] = sdk_version


class DeviceViews:
    def __init__(self, views=None, failed_dump=False, device_link=None):
        self.views = views
        self.failed_dump = failed_dump
        self.device_link = device_link

    def execute_action(self, ui_action_unit: ui_actions.UIActionUnit, text_to_input=None, scroll_direction=None):
        view_client: ViewClient
        view_client, adb_client = self.device_link.create_view_client()
        try:
            view_client.dump()
            view = view_client.findViewById(ui_action_unit.view_id)
            if view is None and ui_action_unit.resourceID is not None and len(ui_action_unit.resourceID)>1:
                view = view_client.findViewById(ui_action_unit.resourceID)
            if view is None and ui_action_unit.text is not None and len(ui_action_unit.text)>1:
                view = view_client.findViewWithText(ui_action_unit.text)
            if view is not None:
                if ui_action_unit.action_type == ui_actions.ACTION_TYPE_TAP:
                    view.touch()
                elif ui_action_unit.action_type == ui_actions.ACTION_TYPE_INPUT:
                    view.setText(text_to_input)
                elif ui_action_unit.action_type == ui_actions.ACTION_TYPE_SCROLL:
                    ui_scrollable = view.uiScrollable
                    if ui_scrollable is not None:
                        if scroll_direction is not None:
                            if ui_actions.ACTION_SCROLL_FLING_FORWARD == scroll_direction:
                                ui_scrollable.flingForward()
                            elif ui_actions.ACTION_SCROLL_FLING_BACKWARD == scroll_direction:
                                ui_scrollable.flingBackward()
                            elif ui_actions.ACTION_SCROLL_FLING_TO_START == scroll_direction:
                                ui_scrollable.flingToBeginning()
                            elif ui_actions.ACTION_SCROLL_FLING_TO_END == scroll_direction:
                                ui_scrollable.flingToEnd()
                            else:
                                ui_scrollable.flingForward()
                        else:
                            ui_scrollable.flingForward()
                    else:
                        return False, f"ACTION cant be taken for view {ui_action_unit.view_id}. uiScrollable not found."
                else:
                    return False, f"ACTION cant be taken for view {ui_action_unit.view_id}. Neither tap or input or scroll."
            else:
                return False, f"ACTION cant be taken for view {ui_action_unit.view_id}. View does not exists."
            time.sleep(DEFAULT_SLEEP)
        finally:
            adb_client.close()
        return True


class DeviceLink:

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.androidSerial = None
        self.secure = None
        self.debuggable = None
        self.device_sdk_build_version = None
        self.versionReleaseProperty = None
        self.buildFingerPrint = None
        self.installed_apps = None
        self.current_view = None
        self.last_view = None
        self.display_width = None
        self.display_height = None
        self.special_log_file = None
        self.serialno = None
        self.emulator_avd_id = None
        self.is_closed = False

    def configure_device(self, serialno: None):
        self.serialno = serialno
        self.androidSerial = None
        adb_client = AdbClient()
        devices = adb_client.getDevices()
        if len(devices) == 0:
            raise RuntimeError("This program requires at least one device connected. None was found.")
        for device in devices:
            if device.status == 'device':
                if serialno is None or serialno == device.serialno:
                    self.androidSerial = device.serialno
                    self.serialno = device.serialno
                    self.logger.info("Using device %s" % self.androidSerial)
                    adb_client.setSerialno(self.androidSerial)
                    break
        if self.androidSerial is None:
            raise RuntimeError("No on-line devices found")
        self.secure = adb_client.getSystemProperty('ro.secure')
        self.debuggable = adb_client.getSystemProperty('ro.debuggable')
        self.device_sdk_build_version = adb_client.getProperty('ro.build.version.sdk')
        self.versionReleaseProperty = adb_client.getProperty('ro.build.version.release')
        self.buildFingerPrint = adb_client.getProperty('ro.bootimage.build.fingerprint')
        self.wait_to_be_ready()
        self.get_installed_apps()
        adb_client.close()

    def _create_adb_client(self):
        try:
            adb_client = AdbClient(serialno=self.serialno)
            adb_client.checkConnected()
            return adb_client
        except:
            tb_exception = traceback.format_exc()
            self.logger.debug(tb_exception)
            raise

    def create_view_client(self):
        try:
            adb_client = self._create_adb_client()
            view_client = ViewClient(device=adb_client, serialno=self.androidSerial, useuiautomatorhelper=False,
                                     autodump=False)
            # display_width = viewClient.display['width']
            # display_height = viewClient.display['height']
            return view_client, adb_client
        except:
            tb_exception = traceback.format_exc()
            self.logger.debug(tb_exception)
            raise

    def update_current_view(self, max_attempts=1, interval=DEFAULT_SLEEP):
        attempt_index = 0
        success = False
        while not success and attempt_index < max_attempts:
            xml_dump = self.uiautomator_dump()
            if xml_dump is not None:
                view_client = AdaptedViewClient(sdk_version=int(self.device_sdk_build_version))
                view_client.setViewsFromUiAutomatorDump(xml_dump)
                views = view_client.views
                self.current_view = DeviceViews(views=views, failed_dump=False, device_link=self)
                success = True
            attempt_index = attempt_index + 1
            time.sleep(interval)
        return success

    def get_current_view(self) -> DeviceViews:
        return self.current_view

    def get_last_view(self) -> DeviceViews:
        return self.last_view

    def refresh_installed_apps(self):
        self.fail_if_not_ready()
        cmd_list = ["adb", "-s", self.androidSerial, "shell", "pm", "list", "packages", "-f"]
        command = Command(cmd=cmd_list)
        command.run(timeout=-1, block=True)
        stdout, stderr = command.collect_outputs()
        return_code = command.process.returncode
        if stdout is not None and return_code == 0:
            app_lines = stdout.splitlines()
            app_line_re = re.compile("package:(?P<apk_path>.+)=(?P<package>[^=]+)")
            packages = []
            for app_line in app_lines:
                m = app_line_re.match(app_line)
                if m:
                    packages.append(m.group('package'))
            self.installed_apps = packages
        else:
            raise RuntimeError(f"Can't list device packages. Failed to execute adb shell. Device {self.serialno}")

    def get_installed_apps(self):
        if self.installed_apps is None or len(self.installed_apps) == 0:
            self.refresh_installed_apps()
        return self.installed_apps

    def get_package_apks(self, package):
        self.fail_if_not_ready()
        cmd_list = ["adb", "-s", self.androidSerial, "shell", "pm", "path", package]
        command = Command(cmd=cmd_list)
        command.run(timeout=-1, block=True)
        stdout, stderr = command.collect_outputs()
        return_code = command.process.returncode
        if stdout is not None and return_code == 0:
            app_pkg_item_re = re.compile("^package:.+/(?P<qualifier>[^/]+)\\.apk$")
            pkgs_lines = stdout.splitlines()
            internal_pkg_items = []
            for pkg_line in pkgs_lines:
                m2 = app_pkg_item_re.match(pkg_line)
                if m2:
                    internal_path = pkg_line.split(':')[1]
                    qualifier = m2.group('qualifier')
                    internal_pkg_items.append({
                        "internal_path": internal_path,
                        "qualifier": qualifier
                    })
            if len(internal_pkg_items) == 0:
                return None
            return internal_pkg_items
        else:
            raise RuntimeError(f"Failed to identify path for package {package}. Device {self.serialno} offline?")

    def get_package_running_pid(self, package):
        self.fail_if_not_ready()
        cmd_list = ["adb", "-s", self.androidSerial, "shell", "pidof", package]
        command = Command(cmd=cmd_list)
        command.run(timeout=-1, block=True)
        stdout, stderr = command.collect_outputs()
        return_code = command.process.returncode
        if stdout is not None and return_code == 0:
            package_pid_re = re.compile(f"^(?P<pid>\\d+)$")
            pid_lines = stdout.splitlines()
            for pid_line in pid_lines:
                m = package_pid_re.match(pid_line)
                if m:
                    pid = m.group('pid')
                    return pid.strip()
            return None
        else:
            raise RuntimeError(f"Failed to identify PID for package {package}. Device {self.serialno} offline?")

    def get_package_uid(self, package):
        self.fail_if_not_ready()
        cmd_list = ["adb", "-s", self.androidSerial, "shell", "pm", "list", "package", "-U", package]
        command = Command(cmd=cmd_list)
        command.run(timeout=-1, block=True)
        stdout, stderr = command.collect_outputs()
        return_code = command.process.returncode
        if stdout is not None and return_code == 0:
            package_uid_re = re.compile(f"^package:{package} uid:(?P<uid>\\d+)$")
            uid_lines = stdout.splitlines()
            for uid_line in uid_lines:
                m = package_uid_re.match(uid_line)
                if m:
                    uid = m.group('uid')
                    return uid.strip()
            return None
        else:
            raise RuntimeError(f"Failed to identify UID for package {package}. Device {self.serialno} offline?")

    def is_installed(self, pkg_name):
        if pkg_name not in self.get_installed_apps():
            self.logger.debug(f"Package {pkg_name} is not in the installed list")
            return False
        return True

    def adb_pull_apk(self, pkg_name, destdir):
        self.fail_if_not_ready()
        assert isinstance(pkg_name, str)
        self.logger.info(f"Pulling pkg {pkg_name}")
        if not self.is_installed(pkg_name):
            self.logger.warning(f"Package {pkg_name} is not in the installed list and can't be pulled out")
            return None
        pkg_items = self.get_package_apks(pkg_name)
        items_taken = []
        for pkg_item in pkg_items:
            pkg_path = pkg_item["internal_path"]
            qualifier = pkg_item["qualifier"]
            if pkg_path is not None:
                file_path = os.path.join(destdir, f"{pkg_name}-{qualifier}.apk")
                pull_cmd = ["adb", "-s", self.androidSerial, "pull", pkg_path, file_path]
                pull_p = subprocess.Popen(pull_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = pull_p.communicate()
                self.logger.debug(" ".join(pull_cmd))
                self.logger.debug(f"Process exited with status: {pull_p.returncode}")
                self.logger.debug(stdout.decode())
                if os.path.exists(file_path):
                    items_taken.append({
                        "path": file_path,
                        "qualifier": qualifier,
                        "internal_path": pkg_path
                    })
        if len(items_taken) == 0:
            self.logger.info("No internal pkg could be found to be pulled")
            return None
        self.logger.info(f"Found {len(items_taken)} internal PKG(s) related to the app {pkg_name}")
        return items_taken

    def to_dict(self):
        device_link = {
            "androidSerial": self.androidSerial,
            "secure": self.secure,
            "debuggable": self.debuggable,
            "device_sdk_build_version": self.device_sdk_build_version,
            "versionReleaseProperty": self.versionReleaseProperty,
            "buildFingerPrint": self.buildFingerPrint,
            "installed_apps": self.installed_apps,
        }
        return device_link

    def get_activity_history(self):
        self.fail_if_not_ready()
        dump_cmd = ["adb", "-s", self.androidSerial, "shell", "dumpsys", "activity", "activities"]
        command = Command(cmd=dump_cmd)
        command.run(timeout=-1, block=True)
        stdout, stderr = command.collect_outputs()
        return_code = command.process.returncode
        history = []
        if return_code == 0 and len(stdout) > 0:
            stdout_lines = stdout.splitlines()
            activity_line_re = re.compile(r'\s+\*\s+Hist\s+#\d+:\sActivityRecord\{\S+\s\S+\s+(\S+).*}')
            for line in stdout_lines:
                m = activity_line_re.search(line)
                if m:
                    history.append(m.group(1))
        return history

    def get_running_services(self):
        self.fail_if_not_ready()
        dump_cmd = ["adb", "-s", self.androidSerial, "shell", "dumpsys", "activity", "services"]
        command = Command(cmd=dump_cmd)
        command.run(timeout=-1, block=True)
        stdout, stderr = command.collect_outputs()
        return_code = command.process.returncode
        history = []
        if return_code == 0 and len(stdout) > 0:
            stdout_lines = stdout.splitlines()
            activity_line_re = re.compile(r'\s+\*\s*ServiceRecord\{\S+\s\S+\s+(\S+).*}')
            for line in stdout_lines:
                m = activity_line_re.search(line)
                if m:
                    history.append(m.group(1))
        return history

    def get_wlan_ip_address(self):
        # adb shell ip addr show wlan0
        self.fail_if_not_ready()
        dump_cmd = ["adb", "-s", self.androidSerial, "shell", "ip", "addr", "show", "wlan0"]
        command = Command(cmd=dump_cmd)
        command.run(timeout=-1, block=True)
        stdout, stderr = command.collect_outputs()
        return_code = command.process.returncode
        if return_code == 0 and len(stdout) > 0:
            stdout_lines = stdout.splitlines()
            ip_re = re.compile('^.+inet\\s+(\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}).+$')
            for line in stdout_lines:
                m = ip_re.search(line)
                if m:
                    ip = m.group(1)
                    return ip
        return None

    def adb_forward_tcp_port(self, local_port, remote_port):
        self.fail_if_not_ready()
        try:
            command = ["adb", "-s", self.androidSerial, "forward", "tcp:%d" % local_port, "tcp:%d" % remote_port]
            subprocess.run(command, check=True)
            self.logger.info("adb forward completed successfully")
        except subprocess.CalledProcessError as e:
            print(f"Error running adb forward: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def adb_pull(self, file, dest_folder, dest_file):
        self.fail_if_not_ready()
        try:
            file_dest_path = os.path.join(dest_folder, dest_file)
            command = ["adb", "-s", self.androidSerial, "pull", file, file_dest_path]
            subprocess.run(command, check=True)
            self.logger.info("adb pull completed successfully")
        except subprocess.CalledProcessError as e:
            print(f"Error running adb forward: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def adb_keyevent(self, key_event):
        key_event_key = KEY_EVENT[key_event]
        if key_event_key is None:
            str_err = "Unknown key_event: choose one of " + ', '.join([key for key in KEY_EVENT])
            raise RuntimeError(str_err)
        adb_client = self._create_adb_client()
        try:
            adb_client.press(key_event)
        finally:
            if adb_client is not None:
                adb_client.close()

    def apps_not_installed(self, pkg_list):
        installed_pkgs = self.get_installed_apps()
        not_installed = [pkg for pkg in pkg_list if pkg not in installed_pkgs]
        return not_installed

    def open_google_play(self, pkg_name):
        return self.open_url(f"https://play.google.com/store/apps/details?id={pkg_name}")

    def open_url(self, url):
        self.fail_if_not_ready()
        cmd_list = ["adb", "-s", self.androidSerial, "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d",
                    url]
        command = Command(cmd=cmd_list)
        command.run(timeout=-1, block=True)
        stdout, stderr = command.collect_outputs()
        success = command.process.returncode == 0 and stdout is not None and "Starting: Intent" in stdout
        if not success:
            self.logger.warning(
                f"Launch URL failed. Return code: {command.process.returncode}. {stdout}\n----\n{stderr}")
        return success, stdout, stderr

    def uninstall_app(self, package_name):
        self.fail_if_not_ready()
        cmd_list = ["adb", "-s", self.androidSerial, "uninstall", package_name]
        command = Command(cmd=cmd_list)
        command.run(timeout=-1, block=True)
        stdout, stderr = command.collect_outputs()
        self.refresh_installed_apps()
        success = package_name not in self.get_installed_apps()
        if not success:
            self.logger.warning(
                f"uninstall_app {package_name} failed. Device {self.serialno}. "
                f"Return code: {command.process.returncode}. {stdout}\n----\n{stderr}")
        self.installed_apps = None
        return success, stdout, stderr

    def install_app(self, base_pkg, splits=None):
        self.fail_if_not_ready()
        if splits is None:
            splits = []
        cmd_list = ["adb", "-s", self.androidSerial, "install", base_pkg] if len(splits) == 0 else ["adb", "-s",
                                                                                                    self.androidSerial,
                                                                                                    "install-multiple",
                                                                                                    base_pkg] + splits
        command = Command(cmd=cmd_list)
        command.run(timeout=-1, block=True)
        stdout, stderr = command.collect_outputs()
        success = command.process.returncode == 0
        if stdout is not None and 'Performing Streamed Install' in stdout:
            success = True
        if not success:
            self.logger.warning(
                f"install_app failed. Return code: {command.process.returncode}. {stdout}\n----\n{stderr}")
        self.installed_apps = None
        return success, stdout, stderr

    def capture_snapshot(self, snapshot_file=None, error_file=None):
        self.fail_if_not_ready()
        dump_cmd = ["adb", "-s", self.androidSerial, "exec-out", "screencap", "-p"]
        if snapshot_file is not None and error_file is not None:
            command = Command(cmd=dump_cmd, stdout_file=snapshot_file, stderr_file=error_file)
            command.run(timeout=-1, block=True)
            stdout, stderr = command.collect_outputs()
            snap_size = 0
            if os.path.isfile(stdout):
                return os.path.getsize(stdout)
            success = snap_size > 0
            if not success:
                self.logger.warning(
                    f"Failed to obtain screenshot.")
                return None
            return success
        else:
            command = Command(cmd=dump_cmd, stdout_file=snapshot_file, stderr_file=error_file,
                              produces_binary_output=True)
            command.run(timeout=-1, block=True)
            stdout, stderr = command.collect_outputs()
            if len(stderr) > 0:
                return None
            if len(stdout) > 0:
                return stdout
            return None

    def uiautomator_dump(self):
        self.fail_if_not_ready()
        dump_cmd = ["adb", "-s", self.androidSerial, "exec-out", "uiautomator", "dump", "/dev/tty"]
        command = Command(cmd=dump_cmd)
        command.run(timeout=-1, block=True)
        stdout, stderr = command.collect_outputs()
        success = "<?xml version" in stdout
        if not success:
            self.logger.warning(
                f"Failed to obtain UIAutomator view dump: {command.process.returncode}. {stdout}\n----\n{stderr}")
            return None
        return stdout

    def grant_permission(self, package_name, permission):
        self.fail_if_not_ready()
        dump_cmd = ["adb", "-s", self.androidSerial, "shell", "pm", "grant", package_name, permission]
        command = Command(cmd=dump_cmd)
        command.run(timeout=-1, block=True)
        stdout, stderr = command.collect_outputs()
        return_code = command.process.returncode
        if return_code == 0:
            return True, stdout, stderr
        self.logger.debug(stdout)
        self.logger.debug(stderr)
        return False, stdout, stderr

    def launch_app(self, base_pkg, wait_on_success=DEFAULT_SLEEP):
        self.fail_if_not_ready()
        cmd_list = ["adb", "-s", self.androidSerial, "shell", "monkey", "-p", base_pkg, "-c",
                    "android.intent.category.LAUNCHER", "1"]
        command = Command(cmd=cmd_list)
        command.run(timeout=-1, block=True)
        stdout, stderr = command.collect_outputs()
        success = command.process.returncode == 0
        if not success:
            self.logger.warning(
                f"launch_app failed. Return code: {command.process.returncode}. {stdout}\n----\n{stderr}")
        self.logger.info(f"Launched app {base_pkg} and waiting {wait_on_success}s")
        time.sleep(wait_on_success)
        return success, stdout, stderr

    def monkey_tester(self, base_pkg, event_count):
        self.fail_if_not_ready()
        cmd_list = ["adb", "-s", self.androidSerial, "shell", "monkey", "-p", base_pkg, "--pct-syskeys", "0",
                    "--pct-touch", "100", "--throttle", "2000", "-v", str(event_count)]
        command = Command(cmd=cmd_list)
        command.run(timeout=-1, block=True)
        stdout, stderr = command.collect_outputs()
        success = command.process.returncode == 0
        if not success:
            self.logger.warning(
                f"monkey tester failed. Return code: {command.process.returncode}. {stdout}\n----\n{stderr}")
        return success, stdout, stderr

    def restore_emulator_snapshot(self, snapshot_name):
        cmd_list = ["adb", "-s", self.androidSerial, "emu", "avd", "snapshot", "load", snapshot_name]
        command = Command(cmd=cmd_list)
        command.run(timeout=-1, block=True)
        stdout, stderr = command.collect_outputs()
        if "OK" in stdout:
            return True
        return False

    def create_emulator_snapshot(self, snapshot_name):
        cmd_list = ["adb", "-s", self.androidSerial, "emu", "avd", "snapshot", "save", snapshot_name]
        command = Command(cmd=cmd_list)
        command.run(timeout=-1, block=True)
        stdout, stderr = command.collect_outputs()
        if "OK" in stdout:
            return True
        return False

    def list_emulator_snapshots(self):
        cmd_list = ["adb", "-s", self.androidSerial, "emu", "avd", "snapshot", "list"]
        command = Command(cmd=cmd_list)
        command.run(timeout=-1, block=True)
        stdout, stderr = command.collect_outputs()
        stdout_lines = stdout.splitlines()
        pattern = re.compile(r'^(?P<id>\S+)\s+(?P<tag>\S+).*$')
        result = []
        if 'List of snapshots present on all disks:' in stdout_lines[0]:
            for item in stdout_lines[1:-1]:
                if "VM CLOCK" in item:
                    continue
                if len(item) < 5:
                    continue
                match = pattern.match(item)
                if match:
                    group_dict = match.groupdict()
                    result.append(group_dict["tag"])
        return result

    def reboot(self):
        cmd_list = ["adb", "-s", self.androidSerial, "reboot"]
        command = Command(cmd=cmd_list)
        command.run(timeout=-1, block=True)
        stdout, stderr = command.collect_outputs()
        if len(stdout) < 10 and len(stderr) < 10:
            return True
        return False

    def get_avd_id(self):
        if self.emulator_avd_id is None:
            cmd_list = ["adb", "-s", self.androidSerial, "emu", "avd", "id"]
            command = Command(cmd=cmd_list)
            command.run(timeout=-1, block=True)
            stdout, stderr = command.collect_outputs()
            if "OK" in stdout:
                lines = stdout.splitlines()
                for line in lines:
                    if line != "OK":
                        self.emulator_avd_id = line
                        break
        return self.emulator_avd_id

    def is_emulator(self):
        return "emulator" in self.serialno

    def is_active(self):
        connected_devices = list_adb_devices()
        if self.serialno in connected_devices:
            cmd_list = ["adb", "-s", self.androidSerial, "shell", "date"]
            command = Command(cmd=cmd_list)
            command.run(timeout=-1, block=True)
            stdout, stderr = command.collect_outputs()
            current_year = str(datetime.now().year)
            if stdout is not None and current_year in stdout:
                return True
        return False

    def is_display_on(self):
        connected_devices = list_adb_devices()
        if self.serialno in connected_devices:
            cmd_list = ["adb", "-s", self.androidSerial, "shell", "dumpsys", "display"]
            command = Command(cmd=cmd_list)
            command.run(timeout=-1, block=True)
            stdout, stderr = command.collect_outputs()
            if stdout is not None and "Display State=ON" in stdout:
                return True
            else:
                return False
        return False

    def kill_emulator(self):
        if self.is_emulator():
            cmd_list = ["adb", "-s", self.androidSerial, "emu", "kill"]
            command = Command(cmd=cmd_list)
            command.run(timeout=-1, block=True)
            stdout, stderr = command.collect_outputs()
            if stdout is not None and 'OK: killing emulator' in stdout:
                return True
            else:
                return False
        return False

    def wait_to_be_ready(self, interval=DEFAULT_SLEEP, max_wait_cycles=-1):
        is_ready = False
        current_wait_cycle = 0
        while not is_ready and not self.is_closed:
            is_ready = self.is_ready()
            if is_ready:
                break
            else:
                self.logger.debug(f"Device is not ready... waiting {interval}s")
                time.sleep(interval)
            if max_wait_cycles > -1:
                if current_wait_cycle > max_wait_cycles:
                    raise RuntimeError(f"Device is not ready. Max wait timeout exceeded...")
            current_wait_cycle = current_wait_cycle + 1

    def wait_for_app_to_start(self, package_name, interval=DEFAULT_SLEEP, max_wait_cycles=12):
        is_running = False
        current_wait_cycle = 0
        while not is_running and not self.is_closed:
            pid = self.get_package_running_pid(package=package_name)
            if pid is not None:
                return pid
            if max_wait_cycles > -1:
                if current_wait_cycle > max_wait_cycles:
                    raise RuntimeError(f"Package {package_name} didn't start. Timeout reached")
            current_wait_cycle = current_wait_cycle + 1
            time.sleep(interval)
        return None

    def wait_to_be_installed(self, package_name, interval=5, max_intervals_to_wait=30):
        is_installed = False
        curr_interval_count = 0
        while not is_installed and not self.is_closed and curr_interval_count < max_intervals_to_wait:
            if package_name in self.get_installed_apps():
                return True
            else:
                self.refresh_installed_apps()
                self.logger.info(
                    f"Package {package_name} is not in the installed list. Waiting... Device {self.serialno}")
                time.sleep(interval)
            curr_interval_count = curr_interval_count + 1
        return is_installed

    def wait_to_be_uninstalled(self, package_name, interval=60, max_intervals_to_wait=20):
        was_uninstalled = False
        curr_interval_count = 0
        while not was_uninstalled and not self.is_closed and curr_interval_count < max_intervals_to_wait:
            if package_name not in self.get_installed_apps():
                return True
            else:
                self.refresh_installed_apps()
                self.logger.debug(f"Package {package_name} is in the installed list. Waiting... Device {self.serialno}")
                time.sleep(interval)
            curr_interval_count = curr_interval_count + 1
        return was_uninstalled

    def fail_if_not_ready(self, max_retry_count=20, interval=5):
        curr_retry_count = 0
        while curr_retry_count < max_retry_count and not self.is_closed:
            if self.is_ready():
                return True
            curr_retry_count = curr_retry_count + 1
            time.sleep(interval)
        raise RuntimeError(DEFAULT_LOST_CONNECTION_MSG)

    def is_ready(self):
        is_active = self.is_active()
        is_display_on = self.is_display_on()
        return is_active and is_display_on and not self.is_closed

    def close_connection(self):
        self.is_closed = True


def main():
    device_link = DeviceLink()
    device_link.configure_device(serialno=None)
    pos = 0
    while True:
        print("waiting...")
        time.sleep(5)
        snapshot = device_link.capture_snapshot()
        if snapshot is not None:
            with open(f"./snapshot_{pos}.png", 'wb') as file:
                file.write(snapshot)
        pos = pos + 1


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG)
    main()
