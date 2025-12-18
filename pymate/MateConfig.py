import logging
import os.path

from pymate.utils.utils import *
from pymate.SpecialLog import SpecialLog

BLACKLIST = ["003_native_file_access.js"]
DEFAULT_TIMEOUT = -1
DEFAULT_EVENT_INTERVAL = 4
DEFAULT_INPUT_CFG_DIR = os.path.join(".", "input")
DEFAULT_TMP_DIR = os.path.join(".", "tmp")
DEFAULT_TOOLS_DIR = os.path.join(".", "tools")
DEFAULT_OUTPUT_DIR = os.path.join(".", "output")


def is_windows():
    return os.name == 'nt'


class MateConfig:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MateConfig, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.logger = logging.getLogger(self.__class__.__name__)
            self.input_dir = None
            self.output_dir = None
            self.tmp_dir = None
            self.tools_dir = None
            self.run_interceptors = None
            self.run_enumerators = None
            self.frida_script = None
            self.timeout = None
            self.event_interval = None
            self.merge_multiple_apks = None
            self.set_debuggable_flag = None
            self.set_allow_backup_flag = None
            self.tools_misc_dir = None
            self.tool_apk_editor = None
            self.tool_apktool = None
            self.tool_zipalign = None
            self.tool_apksigner = None
            self.tool_apksigner_key = None
            self.tool_apksigner_cert = None
            self.no_compile_ts = None
            self.special_logs = {}
            self.special_logs_dir = None
            self.tool_dex2jar_base_dir = None
            self.tool_dex2jar = None
            self.tool_jar2dex = None
            self.initialized = True

    def configure(self, input_dir,
                  output_dir,
                  tmp_dir,
                  tools_dir,
                  run_interceptors,
                  run_enumerators,
                  timeout=DEFAULT_TIMEOUT,
                  event_interval=DEFAULT_EVENT_INTERVAL,
                  merge_multiple_apks=False,
                  set_debuggable_flag=False,
                  set_allow_backup_flag=False):
        self.logger.debug(f"Configuration - interceptors:{self.run_interceptors} - enumerators:{self.run_enumerators}")

        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)
        if not os.path.isdir(tmp_dir):
            os.makedirs(tmp_dir)
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.special_logs_dir = os.path.join(self.output_dir, "logs")
        if not os.path.isdir(self.special_logs_dir):
            os.makedirs(self.special_logs_dir)
        self.tmp_dir = tmp_dir
        self.tools_dir = tools_dir
        self.run_interceptors = run_interceptors
        self.run_enumerators = run_enumerators
        self.frida_script = None
        self.timeout = timeout
        self.event_interval = event_interval
        self.merge_multiple_apks = merge_multiple_apks
        self.set_debuggable_flag = set_debuggable_flag
        self.set_allow_backup_flag = set_allow_backup_flag
        self.tools_misc_dir = os.path.join(self.tools_dir, "misc")
        self.tool_apk_editor = os.path.join(self.tools_misc_dir, "APKEditor.jar")
        self.tool_apktool = os.path.join(self.tools_misc_dir, "apktool.jar")
        self.tool_zipalign = os.path.join(self.tools_misc_dir, "zipalign.exe")
        self.tool_apksigner = os.path.join(self.tools_misc_dir, "apksigner.jar")
        self.tool_apksigner_key = os.path.join(self.tools_misc_dir, "signkey.pk8")
        self.tool_apksigner_cert = os.path.join(self.tools_misc_dir, "signkey.x509.pem")
        self.tool_dex2jar_base_dir = os.path.join(self.tools_misc_dir, "dex-tools")
        if is_windows():
            self.tool_dex2jar = os.path.join(self.tool_dex2jar_base_dir, "d2j-dex2jar.bat")
            self.tool_jar2dex = os.path.join(self.tool_dex2jar_base_dir, "d2j-jar2dex.bat")
        else:
            self.tool_dex2jar = os.path.join(self.tool_dex2jar_base_dir, "d2j-dex2jar.sh")
            self.tool_jar2dex = os.path.join(self.tool_dex2jar_base_dir, "d2j-jar2dex.sh")
        interceptors = {}
        enumerators = {}
        stack = [self.input_dir]
        while stack:
            current_directory = stack.pop()
            for filename in os.listdir(current_directory):
                file_path = os.path.join(current_directory, filename)
                if os.path.isdir(file_path):
                    stack.append(file_path)
                else:
                    if filename.endswith(".ts"):
                        if "interceptors" in file_path:
                            interceptors[file_path] = get_number_from_filename(filename)
                        elif "enumerators" in file_path:
                            enumerators[file_path] = get_number_from_filename(filename)
        # Sort files in intercepts and enumerates dictionaries based on the extracted numbers
        sorted_intercepts = {k: v for k, v in sorted(interceptors.items(), key=lambda item: item[1])}
        sorted_enumerates = {k: v for k, v in sorted(enumerators.items(), key=lambda item: item[1])}

        interceptors_script_ts = join_scripts(sorted_intercepts, BLACKLIST, 'Interceptor')
        enumerators_script_ts = join_scripts(sorted_enumerates, BLACKLIST, 'Enumerator')
        if self.run_interceptors and self.run_enumerators:
            final_frida_script_js = compile_ts(interceptors_script_ts + "\n\n\n" + enumerators_script_ts)
        else:
            if self.run_interceptors:
                final_frida_script_js = interceptors_script_ts
            else:
                final_frida_script_js = enumerators_script_ts
        self.frida_script = final_frida_script_js

    def get_app_bag_output_dir(self):
        app_bag_dir = os.path.join(self.output_dir, "AppBag")
        if not os.path.exists(app_bag_dir):
            os.makedirs(app_bag_dir)
        return app_bag_dir

    def get_app_base_output_dir(self, app_pkg_name: str):
        base_pkg_output_dir = os.path.join(self.get_app_bag_output_dir(), app_pkg_name)
        if not os.path.exists(base_pkg_output_dir):
            os.makedirs(base_pkg_output_dir)
        return base_pkg_output_dir

    def get_special_log(self, tag: str) -> SpecialLog:
        if tag in self.special_logs:
            return self.special_logs[tag]
        else:
            log = SpecialLog(base_dir=self.special_logs_dir, tag=tag)
            self.special_logs[tag] = log
            return log

    def start_tool_log(self, tool_name):
        special_log = self.get_special_log("tools-log")
        special_log.begin_timed_operation(qualifier=tool_name)

    def end_tool_log(self, tool_name, success_flag=False, external_command="", exception_str="", extra_data=[],
                     stdout="", stderr=""
                     ):
        special_log = self.get_special_log("tools-log")
        log_data = [success_flag, external_command, exception_str] + extra_data + [stdout, stderr]
        special_log.end_timed_operation(msg="Tool execution", qualifier=tool_name,
                                        extra_data=log_data)

    def to_dict(self):
        config = {
            "input_dir": self.input_dir,
            "output_dir": self.output_dir,
            "tmp_dir": self.tmp_dir,
            "run_interceptors": self.run_interceptors,
            "run_enumerators": self.run_enumerators,
            "timeout": self.timeout,
            "event_interval": self.event_interval
        }
        return config


def create_test_configuration():
    from dotenv import load_dotenv
    load_dotenv()
    config = MateConfig()
    config.configure(
        input_dir=DEFAULT_INPUT_CFG_DIR,
        output_dir=DEFAULT_OUTPUT_DIR,
        tmp_dir=DEFAULT_TMP_DIR,
        tools_dir=DEFAULT_TOOLS_DIR,
        run_interceptors=False,
        run_enumerators=False,
        timeout=-1,
        event_interval=-1,
        merge_multiple_apks=True,
        set_debuggable_flag=True,
        set_allow_backup_flag=True
    )
    return config
