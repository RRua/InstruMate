import logging
import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from tabnanny import check

from pymate.common.app import App
from pymate.device_link import DeviceLink, adb_kill_server
from pymate.device_link import DevicePool
from pymate.device_observer import LogCatObserver, DeviceViewObserver, DeviceViewState
from pymate.instrumate.instrumate_checker_log import InstrumateCheckerLog
from pymate.utils import utils


class InstrumateChecker:
    # Class variable to keep track of the number of instances
    _id_counter = -1

    def __init__(self, output_dir: str, instrumate_checker_log: InstrumateCheckerLog = None,
                 default_launch_wait_timeout=60):
        # Increment the counter and assign the new value to the instance's ID
        InstrumateChecker._id_counter += 1
        self.ID = InstrumateChecker._id_counter
        self.logger = logging.getLogger(self.__class__.__name__)
        self.output_dir = output_dir
        self.instrumate_checker_log = instrumate_checker_log
        self.default_launch_wait_timeout = default_launch_wait_timeout
        self.monkey_loops = 0
        self.qtd_monkey_events = 2
        self.default_delay_after_failure = 4
        self.default_delay_after_success = 2

    def _execute_device_link_command(self, app: App, func, action_msg: str, attempts=3, *args, **kwargs):
        qtd_failed = 0
        success = False
        while not success and qtd_failed < attempts:
            start_time = time.time()
            try:
                success, stdout, stderr = func(*args, **kwargs)
                end_time = time.time()
                duration = end_time - start_time
                self.instrumate_checker_log.log_command_execution(app=app, action=action_msg, success=success,
                                                                  stdout=stdout,
                                                                  stderr=stderr,
                                                                  traceback_exception=None,
                                                                  attempt_index=qtd_failed, total_secs=duration)
                if not success:
                    qtd_failed = qtd_failed + 1
                    time.sleep(self.default_delay_after_failure)
            except Exception:
                tb_exception = traceback.format_exc()
                end_time = time.time()
                duration = end_time - start_time
                self.instrumate_checker_log.log_command_execution(app=app, action=action_msg, success=success,
                                                                  stdout=None,
                                                                  stderr=None,
                                                                  traceback_exception=tb_exception,
                                                                  attempt_index=qtd_failed, total_secs=duration)
                qtd_failed = qtd_failed + 1
                time.sleep(self.default_delay_after_failure)
        if success:
            time.sleep(self.default_delay_after_success)
        return success

    def _uninstall_app(self, app: App, device_link: DeviceLink):
        def do_uninstall():
            success, stdout, stderr = device_link.uninstall_app(app.get_package_name())
            return success, stdout, stderr

        return self._execute_device_link_command(app=app, func=do_uninstall, action_msg="uninstall app")

    def _install_app(self, app: App, device_link: DeviceLink):
        def do_install():
            success, stdout, stderr = device_link.install_app(app.get_base_pkg(), app.get_split_pkgs())
            if success:
                device_link.wait_to_be_installed(package_name=app.get_package_name(), max_intervals_to_wait=10)
            return success, stdout, stderr

        return self._execute_device_link_command(app=app, func=do_install, action_msg="install app")

    def _grant_permissions(self, app: App, device_link: DeviceLink):
        def do_grant_permissions():
            permissions = app.get_permissions()
            concatenated_stdout = ''
            for permission in permissions:
                success, stdout, stderr = device_link.grant_permission(package_name=app.get_package_name(),
                                                                       permission=permission)
                concatenated_stdout = concatenated_stdout + f"permission:{permission}; success: {success}; stdout:{stdout}; stderr: {stderr}\n"
            return True, concatenated_stdout, ""

        return self._execute_device_link_command(app=app, func=do_grant_permissions, action_msg="grant permissions")

    def _check_app_pid(self, app: App, device_link: DeviceLink):
        def do_check_app_pid():
            if not app.get_package_name() in device_link.get_installed_apps():
                msg = f"Can' identify PID. App {app.get_package_name()} is not installed"
                return False, msg, msg
            package_pid = device_link.get_package_running_pid(app.get_package_name())
            if package_pid is None:
                msg = f"Can' identify PID. App {app.get_package_name()} is not running"
                return False, msg, msg
            msg = f"PID Found: App {app.get_package_name()} is running with PID {package_pid}"
            return True, msg, msg

        return self._execute_device_link_command(app=app, func=do_check_app_pid, action_msg="find PID")

    def _check_app_view(self, app: App, view_observer: DeviceViewObserver):
        def do_check_app_view():
            view_state: DeviceViewState = view_observer.observe()
            if view_state is not None and view_state.is_on_launcher_window():
                msg = f"App {app.get_package_name()} is on launcher window after launch"
                return False, msg, msg
            if view_state is not None and not view_state.contains_view_components():
                msg = f"App {app.get_package_name()} contains no view components"
                return False, msg, msg
            msg = f"View Found: App {app.get_package_name()}"
            return True, msg, msg

        return self._execute_device_link_command(app=app, func=do_check_app_view, action_msg="check app view")

    def _launch_app(self, app: App, device_link: DeviceLink):
        def do_launch():
            wait_timeout = self.default_launch_wait_timeout
            if app.is_variant():
                wait_timeout = 2 * self.default_launch_wait_timeout
            success, stdout, stderr = device_link.launch_app(app.get_package_name(),
                                                             wait_on_success=wait_timeout)
            return success, stdout, stderr

        return self._execute_device_link_command(app=app, func=do_launch, action_msg="launch app")

    def _monkey_tester(self, app: App, device_link: DeviceLink):
        def do_monkey_tester():
            success, stdout, stderr = device_link.monkey_tester(app.get_package_name(),
                                                                self.qtd_monkey_events)
            return success, stdout, stderr

        return self._execute_device_link_command(app=app, func=do_monkey_tester, action_msg="launch monkey tester")

    def _capture_view(self, app: App, view_observer: DeviceViewObserver):
        def do_observe_and_save():
            view_state = view_observer.observe()
            if view_state is None:
                return False, "view state is none", ""
            if view_state.is_on_launcher_window():
                msg = f"App {app.get_package_name()} is on launcher window after launch"
                return False, msg, msg
            if not view_state.contains_view_components():
                msg = f"App {app.get_package_name()} contains no view components"
                return False, msg, msg
            view_observer.save(view_state)
            state = view_state.state_dict
            if state is not None:
                if "view_components" in state:
                    for key in state["view_components"]:
                        value = state["view_components"][key]
                        self.instrumate_checker_log.log_app_view_state_component(app, value["signature"],
                                                                                 value["android_class"],
                                                                                 value["package"], value["uniqueId"],
                                                                                 value["parentUniqueId"],
                                                                                 value["resourceID"],
                                                                                 value["contentDesc"], value["text"],
                                                                                 value["checkable"], value["checked"],
                                                                                 value["clickable"],
                                                                                 value["enabled"], value["focusable"],
                                                                                 value["focused"],
                                                                                 value["scrollable"],
                                                                                 value["visibility"], value["password"],
                                                                                 value["selected"])
                if "action_units" in state:
                    for key in state["action_units"]:
                        value = state["action_units"][key]
                        self.instrumate_checker_log.log_app_view_state_action_unit(app, value["view_signature"],
                                                                                   value["view_id"], value["cls"],
                                                                                   value["pkg"], value["label"],
                                                                                   value["type"])
                if "activity_history" in state:
                    for act in state["activity_history"]:
                        self.instrumate_checker_log.log_running_activity(app, act)
                return True, "", ""
            else:
                return False, "", ""

        return self._execute_device_link_command(app=app, func=do_observe_and_save, action_msg="observe view state")

    def _initial_setup(self, app: App, view_observer: DeviceViewObserver):
        def do_initial_setup():
            view_state: DeviceViewState = view_observer.observe()
            if view_state is None:
                return False, "can't capture any view to check if there are pending permissions", "viewstate is none"
            if view_state.is_on_launcher_window():
                return False, "can't do initial setup because device is on launcher window", ""
            if view_state.is_on_permissions_settings_view():
                view_state.allow_permission_settings()
                return False, "allow_permission_settings", "allow_permission_settings"
            if view_state.is_on_full_screen_alert_view():
                view_state.accept_full_screen()
                return False, "accept_full_screen", "accept_full_screen"
            if view_state.is_on_app_not_responding_view():
                view_state.close_not_responding_app()
                return False, "close_not_responding_app", "close_not_responding_app"
            if view_state.is_on_agree_window():
                view_state.close_agree_window()
                return False, "close_agree_window", "close_agree_window"
            return True, "finished_no_action", ""

        return self._execute_device_link_command(app=app, func=do_initial_setup, action_msg="initial app setup",
                                                 attempts=3)

    def _capture_logcat(self, app, logcat_observer: LogCatObserver):
        def do_capture_logcat():
            logcat_state = logcat_observer.observe_and_save()
            state = logcat_state.state_dict
            if state is not None:
                if "parsed_msgs" in state:
                    for item in state["parsed_msgs"]:
                        value = item
                        self.instrumate_checker_log.log_app_logcat_msg(app, value["month"], value["day"], value["time"],
                                                                       value["pid"], value["tid"], value["level"],
                                                                       value["pkg_name"], value["msg"])
                if "exceptions" in state:
                    for item in state["exceptions"]:
                        self.instrumate_checker_log.log_app_exception(app, item)

                if "exception_origins" in state:
                    for item in state["exception_origins"]:
                        self.instrumate_checker_log.log_app_exception_site(app, item["exception_name"], item["method_signature"], item["detail"], item["index"], item["raw_msg"])
                return True, "", ""
            else:
                return False, "", ""

        return self._execute_device_link_command(app=app, func=do_capture_logcat, action_msg="observe logcat state")

    def check_app(self, app: App, device_link: DeviceLink, force_uninstall=True, uninstall_after_finish=False,
                  capture_failed_apps=False):
        view_observer = None
        logcat_observer = None
        try:
            app_output_dir = os.path.join(self.output_dir, f"{app.get_package_name()}-{app.get_app_id()}")
            self.logger.info(f"Checking app {app.get_package_name()} on device {device_link.serialno}")
            if device_link.is_installed(app.get_package_name()) and force_uninstall:
                if not self._uninstall_app(app, device_link=device_link):
                    self.logger.warning(f"Can´t uninstall already installed app {app.get_package_name()} "
                                        f"on device {device_link.serialno}")
                    return False, "can't uninstall app already installed app"
                if not self._install_app(app, device_link=device_link):
                    return False, "can't install app"
            else:
                if not self._install_app(app, device_link=device_link):
                    return False, "can't install app"
            if not self._grant_permissions(app, device_link=device_link):
                return False, "can't grant permissions"
            self.logger.info(f"App {app.get_package_name()} installed on device {device_link.serialno}")
            view_observer = DeviceViewObserver()
            view_observer.configure(target_app=app, device_link=device_link, output_dir=app_output_dir)
            logcat_observer = LogCatObserver()
            logcat_observer.configure(target_app=app, device_link=device_link, output_dir=app_output_dir)
            logcat_observer.start()
            if not self._launch_app(app=app, device_link=device_link):
                return False, "can't launch app"
            self.logger.info(f"App {app.get_package_name()} launched on device {device_link.serialno}")

            self.logger.debug(f"Initial Setup. App: {app.get_package_name()}")
            self._initial_setup(app=app, view_observer=view_observer)

            self.logger.info(f"Initial setup for App {app.get_package_name()} done on device {device_link.serialno}")
            if not self._check_app_pid(app=app, device_link=device_link):
                return False, "can't find app PID"
            if not self._check_app_view(app=app, view_observer=view_observer):
                return False, "App has PID, but window has problems"
            if not self._capture_view(app=app, view_observer=view_observer):
                return False, "can't capture app view"
            if self.monkey_loops > 0:
                for i in range(self.monkey_loops):
                    self.logger.debug(
                        f"About to launch monkey to test app. App: {app.get_package_name()},"
                        f" ID: {app.get_app_id()}")
                    time.sleep(self.default_launch_wait_timeout)
                    if not self._monkey_tester(app, device_link=device_link):
                        return False, "can't launch monkey tester"
                if not self._launch_app(app=app, device_link=device_link):
                    return False, "can't launch app"
                if not self._capture_view(app=app, view_observer=view_observer):
                    return False, "can't capture app view"
            if not self._capture_logcat(app, logcat_observer):
                return False, "can't capture logcat output"

            if uninstall_after_finish:
                if not self._uninstall_app(app, device_link=device_link):
                    self.logger.warning(f"Can´t uninstall app {app.get_package_name()} after finish "
                                        f"on device {device_link.serialno}")
                    return True, "all steps completed, except for the uninstall-after-finish"
            view_observer = None
            logcat_observer = None
            return True, "all steps completed"
        finally:
            if capture_failed_apps:
                if view_observer is not None:
                    try:
                        view_observer.observe_and_save()
                    except:
                        pass
                if logcat_observer is not None:
                    try:
                        logcat_observer.observe_and_save()
                    except:
                        pass
            if logcat_observer is not None:
                logcat_observer.discard()


def worker_on_app(app: App, checker: InstrumateChecker, device_pool: DevicePool, instrumate_log: InstrumateCheckerLog,
                  per_app_attempts=3, capture_failed_apps=False):
    logger = logging.getLogger(f"InstrumateChecker-Worker-({checker.ID} - {app.get_package_name()})")
    app_attempt = 0
    success = False
    device_link = None
    try:
        device_link: DeviceLink = device_pool.get()
        while not success and app_attempt < per_app_attempts:
            logger.info(
                f"Initiated attempt {app_attempt} to health check for App: {app.get_package_name()}, splits:{len(app.get_split_pkgs())}, ID: {app.get_app_id()}")
            start_time = time.time()
            try:
                success, msg = checker.check_app(app=app, device_link=device_link, force_uninstall=app_attempt == 0,
                                                 uninstall_after_finish=False, capture_failed_apps=capture_failed_apps)
                end_time = time.time()
                duration = end_time - start_time
                instrumate_log.log_app_result(app=app, procedure_completed=success, failure_reason=msg,
                                              traceback_exception=None,
                                              total_secs=duration)
                variant_info = "original"
                if app.is_variant():
                    variant_info = f"#{app.get_variant_maker_tag()}-{app.get_variant_feature_labels()}-{app.get_variant_level_labels()}#"
                logger.info(
                    f"Instrumate check finished for App: {app.get_package_name()}-{variant_info}, success: {success}, "
                    f"msg: {msg}, attempt: {app_attempt}, splits:{len(app.get_split_pkgs())}, "
                    f"ID: {app.get_app_id()}, Duration: {duration}s")
            except Exception:
                tb_exception = traceback.format_exc()
                end_time = time.time()
                duration = end_time - start_time
                instrumate_log.log_app_result(app, procedure_completed=False,
                                              failure_reason=f"exception at attempt {app_attempt}",
                                              traceback_exception=tb_exception,
                                              total_secs=duration)
                logger.info(
                    f"Instrumate check failed for App: {app.get_package_name()}, splits:{len(app.get_split_pkgs())}, ID: {app.get_app_id()}, Duration: {duration}s")
                logger.warning(tb_exception)
            app_attempt = app_attempt + 1
        return success
    finally:
        if device_link is not None:
            device_pool.release(device_link)


def worker(apps, device_pool: DevicePool, checker: InstrumateChecker, instrumate_log: InstrumateCheckerLog,
           per_app_attempts=3, capture_failed_apps=False):
    logger = logging.getLogger(f"InstrumateChecker-Worker({checker.ID})")
    qtd_success = 0
    total_time = 0
    current_app_index = 0
    total_apps = len(apps)
    logger.info(f"Worker is about to check {total_apps}.")
    failed_apps = []
    for app in apps:
        start_time = time.time()
        success_on_app = worker_on_app(app=app, device_pool=device_pool, checker=checker, instrumate_log=instrumate_log,
                                       per_app_attempts=per_app_attempts, capture_failed_apps=capture_failed_apps)
        if success_on_app:
            qtd_success = qtd_success + 1
        else:
            failed_apps.append(app)
        end_time = time.time()
        duration = end_time - start_time
        total_time = total_time + duration
        time_spent_so_far = total_time
        average_time = time_spent_so_far / (current_app_index + 1)
        estimated_time_to_finish = average_time * (total_apps - (current_app_index + 1))
        logger.info(
            f"Current app index {current_app_index}. "
            f"Time so far {time_spent_so_far} seconds. "
            f"Time to finish {estimated_time_to_finish}s or {estimated_time_to_finish / 60.0} "
            f"minutes or {estimated_time_to_finish / (60.0 * 60.0)} hours. "
            f"QTD success so far: {qtd_success}, QTD failed so far: {current_app_index + 1 - qtd_success} "
            f"Avg time per item {average_time} seconds. ")
        logger.info("--------------------------")
        current_app_index = current_app_index + 1
    print(f"Worker checked {len(apps)} and {qtd_success} completed successfully while {len(apps) - qtd_success} failed")
    return failed_apps


class InstrumateCheckerManager:
    def __init__(self, config_dir: str = None, output_dir: str = None,
                 device_pool: DevicePool = None, apps=None,
                 iterations=9, monkey_events_per_iteration=500,
                 append_to_existing=False, extra_attempts_for_failed_apps=2, capture_failed_apps=False,
                 attempts_per_app=3):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.output_dir = output_dir
        self.apps = apps
        self.device_pool = device_pool
        self.iterations = iterations
        self.monkey_events_per_iteration = monkey_events_per_iteration
        self.capture_failed_apps = capture_failed_apps
        self.append_to_existing = append_to_existing
        self.attempts_per_app = attempts_per_app
        self.stable_threshold = extra_attempts_for_failed_apps
        sql_post_config_file = os.path.join(config_dir, 'config', 'instrumate_checker_db.sql')
        self.instrumate_checker_log = InstrumateCheckerLog(log_dir=self.output_dir,
                                                           sql_post_config_file=sql_post_config_file)

    def health_check_iteration(self, apps, worker_count, device_pool: DevicePool, attempts_per_app=3,
                               default_launch_wait_timeout=60):
        instrumate_checkers = []
        splits = utils.split_array(apps, worker_count)
        failed_apps = []
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = []
            for k in splits:
                apps = splits[k]
                health_checker = InstrumateChecker(output_dir=self.output_dir,
                                                   instrumate_checker_log=self.instrumate_checker_log,
                                                   default_launch_wait_timeout=default_launch_wait_timeout)
                futures.append(
                    executor.submit(worker, apps, device_pool, health_checker, self.instrumate_checker_log,
                                    attempts_per_app, self.capture_failed_apps))
                instrumate_checkers.append(health_checker)
            for future in as_completed(futures):
                worker_failed_apps = future.result()
                print(f"Worker failed apps: {len(worker_failed_apps)}")
                failed_apps.extend(worker_failed_apps)
        print("Health check iteration ended at :" + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print(f"Total failed apps {len(failed_apps)}")
        print(f"--------------------------------------")
        return failed_apps

    def execute(self):
        start_time = time.time()
        pool_size = self.device_pool.get_size()
        if pool_size == 0:
            raise RuntimeError(f"Can't check any app if the device pool is empty")
        worker_count = max(1, pool_size // 1)
        failed_apps = self.apps
        stable_count = 0
        iteration_count = 0
        max_iterations = self.iterations
        while True:
            print(f"Health check session ----------------")
            print(f"Index: {iteration_count}, Stable count {stable_count}, max iterations: {max_iterations}")
            print(f"Failed apps: {len(failed_apps)}")
            if stable_count > self.stable_threshold:
                break
            if len(failed_apps) == 0 and iteration_count > 0:
                break
            if iteration_count > max_iterations:
                break
            iteration_failed_apps = self.health_check_iteration(apps=failed_apps, worker_count=worker_count,
                                                                device_pool=self.device_pool,
                                                                attempts_per_app=self.attempts_per_app,
                                                                default_launch_wait_timeout=60)
            if len(iteration_failed_apps) == 0:
                failed_apps = []
                break
            last_failed_app_ids = len(failed_apps)
            iteration_failed_app_ids = len(iteration_failed_apps)
            if last_failed_app_ids == iteration_failed_app_ids:
                stable_count = stable_count + 1
            failed_apps = iteration_failed_apps
            print(
                f"Health check iteration {iteration_count} finished. Failed apps {len(failed_apps)}. Stable count {stable_count}")
            print([app.get_package_name() for app in failed_apps])
            print("-----------")
            adb_kill_server()
            iteration_count = iteration_count + 1

        self.logger.info("closing logs")
        self.instrumate_checker_log.close_logs()
        self.logger.info("completed")
        self.logger.info(f"Iterations: {iteration_count}")
        self.logger.info(f"Failed apps: {[app.get_package_name() for app in failed_apps]}")
        # self.device_pool.shutdown()
        end_time = time.time()
        duration = end_time - start_time
        print(f"Took {duration}s or {duration / 60.0} minutes or {duration / (60.0 * 60.0)} hours. ")
        os._exit(0)
