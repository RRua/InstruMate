import sys
import time
from threading import Timer
import os
import logging

import pymate.utils.fs_utils
from pymate.MateConfig import MateConfig
from pymate.device_link import DeviceLink
from pymate.device_link import ProcessMonitor
from pymate.common.app import App
from pymate.utils.utils import write_dict_as_json, copy_file_if_not_exists
from pymate.forensic_state import ViewStateObserver, EnvironmentObserver, MultipleStateObserver, FridaSandboxObserver, \
    SandboxedEnvironmentObserver, FileSystemStateObserver
from pymate.frida_sandbox import FridaConnection
from pymate.action_manager.ActionManager import ActionManager
from pymate.action_manager.policy_strategy.PolicyStrategy import PolicyStrategy
from pymate.action_manager.graph.GraphManager import GraphManager
from pymate.utils import utils


class Project:
    def __init__(self, config: MateConfig,
                 device_link: DeviceLink,
                 process_monitor: ProcessMonitor,
                 app: App,
                 task: str,
                 policy_strategy: PolicyStrategy,
                 destroy_existing_files=False):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = config
        self.device_link = device_link
        self.process_monitor = process_monitor
        self.app = app
        self.project_dir = self.create_project_dir(destroy_existing_files)
        self.states_dir = os.path.join(self.project_dir, "states")
        self.memory_dir = os.path.join(self.project_dir, "memory")
        if not os.path.exists(self.states_dir):
            os.makedirs(self.states_dir)
        if not os.path.exists(self.memory_dir):
            os.makedirs(self.memory_dir)
        self.timer = None
        self.state_observer = None
        self.frida_connection = None
        self.configure_state_observers()
        self.action_manager = ActionManager(project_dir=self.project_dir,
                                            memory_dir=self.memory_dir,
                                            states_dir=self.states_dir,
                                            task=task,
                                            policy_strategy=policy_strategy,
                                            device_link=self.device_link)
        self.graph_manager = GraphManager(graph_dir=self.project_dir, states_dir=self.states_dir)
        self.loop_counter = 0

    def create_project_dir(self, destroy_existing_files) -> str:
        # current_time = datetime.now()
        # folder_name = current_time.strftime("-%Y_%m_%d_%H_%M")
        folder_name = "%s-%s" % (self.app.package_name, self.app.get_version_name())
        base_dir = os.path.join(self.config.output_dir, "MONITOR")
        folder_path = os.path.join(base_dir, folder_name)
        if destroy_existing_files:
            if os.path.exists(folder_path):
                pymate.utils.fs_utils.destroy_dir_files(folder_path)
        os.makedirs(folder_path, exist_ok=True)
        utils.copy_dir_files(src_dir="wwwreport-static", dst_dir=folder_path, src_base_dir=self.config.input_dir)
        print("Current project folder: " + folder_path)
        return folder_path

    def configure_state_observers(self):
        self.frida_connection = FridaConnection.create_frida_connection(base_dir=self.project_dir,
                                                                        app_package=self.app.get_package_name(),
                                                                        compiled_script=self.config.frida_script)
        frida_sandbox_observer = FridaSandboxObserver(frida_connection=self.frida_connection)
        view_state_observer = ViewStateObserver(device_link=self.device_link)
        env_state_observer = EnvironmentObserver(device_link=self.device_link)

        app_private_dir = "/data/data/%s" % self.app.package_name
        device_shared_folder = "/sdcard/"
        filesystem_state_observer = FileSystemStateObserver(app_private_dir=app_private_dir,
                                                            shared_dir=device_shared_folder,
                                                            device_link=self.device_link)
        sandboxed_env_observer = SandboxedEnvironmentObserver(env_observer=env_state_observer,
                                                              frida_sandbox_observer=frida_sandbox_observer)
        self.state_observer = MultipleStateObserver(view_state_observer, sandboxed_env_observer,
                                                    filesystem_state_observer)

    def to_dict(self):
        project = {
            "project_dir": self.project_dir
        }
        return project

    def save_project(self):
        project_dict = self.to_dict()
        config_dict = self.config.to_dict()
        device_dict = self.device_link.to_dict()
        app_dict = self.app.to_dict()
        write_dict_as_json(project_dict, self.project_dir, "project.json")
        write_dict_as_json(config_dict, self.project_dir, "config.json")
        write_dict_as_json(device_dict, self.project_dir, "device.json")
        write_dict_as_json(app_dict, self.project_dir, "app.json")
        dest_apk_name = "%s_%s.apk" % (self.app.package_name, self.app.get_version_name())
        copy_file_if_not_exists(self.app.apk_path, dest_apk_name, dest_base_dir=self.project_dir)

    def start_wwwreport(self):
        import subprocess
        import sys
        import webbrowser
        python_interpreter = sys.executable
        wwwreport_dir = os.path.join(".", "wwwreport")
        script = os.path.join(wwwreport_dir, "http-server.py")
        static_files = os.path.join(wwwreport_dir, "build")
        detached_process = subprocess.Popen([python_interpreter, script, static_files, self.project_dir],
                                            start_new_session=True)
        print(f"Started detached process with PID: {detached_process.pid}")
        print(f"Report http server folders {static_files} and {self.project_dir}")
        webbrowser.open_new("http://localhost:8000")

    def start(self):
        self.logger.info("Starting ForensicMate Project")
        self.logger.info("Starting frida connection (wait...)")
        self.frida_connection.start()
        time.sleep(70)
        try:
            if self.config.timeout > 0:
                self.timer = Timer(self.config.timeout, self.stop)
                self.timer.start()
            while True:
                if self.state_observer is not None:
                    try:
                        self.logger.info("Observing...")
                        self.device_link.dump_device_view_deprecated()
                        self.state_observer.observe()
                        if self.state_observer.has_changed():
                            self.state_observer.save_2_folder(self.states_dir)
                        current_state = self.state_observer.get_state()
                        last_state = self.state_observer.get_last_state()
                        transition_from = last_state.get_signature() if last_state is not None else 'None'
                        transition_to = current_state.get_signature() if current_state is not None else 'None'
                        if current_state is not None:
                            self.graph_manager.update_current_state(multiple_state_item=current_state)
                        strategy_result = self.action_manager.apply_policy_strategy()
                        policy_executed = strategy_result["policy_info"]["success"]
                        transition_dict = {
                            "from_state": transition_from,
                            "to_state": transition_to,
                            "strategy_result": strategy_result
                        }
                        transition_classifier = "With_Policy" if policy_executed is not None and policy_executed else 'Without_Policy'
                        if self.state_observer.has_changed():
                            self.graph_manager.add_state_transition_dict(transition_dict=transition_dict,
                                                                         policy_classifier=transition_classifier,
                                                                         from_signature=transition_from,
                                                                         to_signature=transition_to)
                            write_dict_as_json(transition_dict, self.states_dir,
                                               "Transition_%s_from_%s_to_%s.json" % (
                                                   transition_classifier, transition_from, transition_to))
                        self.graph_manager.save_graph_vis_json()
                        if self.loop_counter == 0:
                            self.start_wwwreport()
                        self.loop_counter = self.loop_counter + 1
                    except Exception:
                        import traceback
                        traceback.print_exc()
                        print(traceback.format_exc())
                        continue
                time.sleep(self.config.event_interval)

        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt.")
            pass
        except Exception:
            import traceback
            traceback.print_exc()
            self.stop()
            sys.exit(-1)

        self.stop()
        self.logger.info("DroidBot Stopped")

    def stop(self):
        pass
