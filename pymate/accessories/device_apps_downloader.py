import logging
import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from pymate.accessories.downloader_log import AppDownloaderLog
from pymate.device_link import DeviceLink
from pymate.device_link import DevicePool
from pymate.device_link.device_link_commander import DeviceLinkCommander
from pymate.device_observer import DeviceViewObserver, DeviceViewState
from pymate.common.app import App
from pymate.utils import utils


class GooglePlayAppDownloader(DeviceLinkCommander):
    def __init__(self, device_pool: DevicePool, output_dir: str, downloader_log: AppDownloaderLog = None):
        super().__init__(device_pool=device_pool, output_dir=output_dir)
        self.downloader_log = downloader_log

    def _launch_app_at_google_play(self, pkg_name: str, device_link: DeviceLink):
        def do_launch_app_at_google_play():
            success, stdout, stderr = device_link.open_google_play(pkg_name)
            return success, stdout, stderr

        def logger_function(success, duration, attempt_index, stdout, stderr, tb_exception):
            self.downloader_log.log_downloader_action(package_name=pkg_name,
                                                      summary_msg="launch app at google play",
                                                      success=success,
                                                      attempt_index=attempt_index,
                                                      stdout=stdout, stderr=stderr,
                                                      traceback_exception=tb_exception,
                                                      total_secs=duration)

        return self._execute_device_link_command(func=do_launch_app_at_google_play, logger_func=logger_function)

    def _uninstall(self, pkg_name: str, device_link: DeviceLink):
        def do_uninstall():
            self.logger.info(f"Uninstalling app {pkg_name}")
            success, stdout, stderr = device_link.uninstall_app(pkg_name)
            if success:
                device_link.wait_to_be_uninstalled(package_name=pkg_name)
            return success, stdout, stderr

        def logger_function(success, duration, attempt_index, stdout, stderr, tb_exception):
            self.downloader_log.log_downloader_action(package_name=pkg_name,
                                                      summary_msg="uninstall",
                                                      success=success,
                                                      attempt_index=attempt_index,
                                                      stdout=stdout, stderr=stderr,
                                                      traceback_exception=tb_exception,
                                                      total_secs=duration)

        return self._execute_device_link_command(func=do_uninstall, logger_func=logger_function)

    def _click_install_or_update_and_pull(self, pkg_name: str, view_observer: DeviceViewObserver(),
                                          device_link: DeviceLink, output_dir: str):
        def do_observe_and_save():
            view_state: DeviceViewState = view_observer.observe_and_save()
            if view_state is None:
                return False, "Couldn't capture device view", ""
            ui_action_unit = view_state.find_action_unit_by_text("Install")
            if ui_action_unit is None:
                ui_action_unit = view_state.find_action_unit_by_text("Open")
            if ui_action_unit is None:
                ui_action_unit = view_state.find_action_unit_by_text("Update")
            incompatible = view_state.find_view_component_by_text("isn't compatible with this")
            unavailable = view_state.find_view_component_by_text("isn't available")
            if incompatible is not None:
                return False, "This phone isn't compatible with this app or version", ""
            if unavailable:
                return False, "Unavailable in region", ""
            if ui_action_unit is not None:
                if ui_action_unit.text != "Open":
                    view_state.device_view.execute_action(ui_action_unit=ui_action_unit)
                device_link.wait_to_be_installed(package_name=pkg_name, max_intervals_to_wait=10)
                items_taken = device_link.adb_pull_apk(pkg_name=pkg_name, destdir=output_dir)
                if items_taken is None:
                    return False, "Failed to pull installation packages", ""
                else:
                    return True, "Installed and pulled apps", ""
            else:

                return False, "Can't find Install or Update buttons in view", ""

        def logger_function(success, duration, attempt_index, stdout, stderr, tb_exception):
            self.downloader_log.log_downloader_action(package_name=pkg_name,
                                                      summary_msg="install or update and pull",
                                                      success=success,
                                                      attempt_index=attempt_index,
                                                      stdout=stdout, stderr=stderr,
                                                      traceback_exception=tb_exception,
                                                      total_secs=duration)

        return self._execute_device_link_command(func=do_observe_and_save, logger_func=logger_function)

    def download_app(self, pkg_name, force_uninstall_if_installed=False, uninstall_after_finish=True):
        app_output_dir = os.path.join(self.output_dir, f"{pkg_name}")
        device_link: DeviceLink = self.device_pool.get()
        try:
            self.logger.info(f"Downloading app {pkg_name} on device {device_link.serialno}")
            if device_link.is_installed(pkg_name) and force_uninstall_if_installed:
                if not self._uninstall(pkg_name, device_link=device_link):
                    return False, "can't uninstall app"
            if not self._launch_app_at_google_play(pkg_name, device_link=device_link):
                return False, "can't launch google play"
            view_observer = DeviceViewObserver()
            view_observer.configure(target_app=None, device_link=device_link, output_dir=app_output_dir)
            if not self._click_install_or_update_and_pull(pkg_name, view_observer, device_link=device_link,
                                                          output_dir=app_output_dir):
                return False, "can't click on install or update and pull the app"
            if uninstall_after_finish:
                if not self._uninstall(pkg_name, device_link=device_link):
                    return True, "can't uninstall app after finish"
            return True, "all steps completed"
        finally:
            self.device_pool.release(device_link)


def worker(app_pkgs, app_downloader: GooglePlayAppDownloader, downloader_log: AppDownloaderLog):
    logger = logging.getLogger(f"GooglePlayAppDownloader-Worker({app_downloader.ID})")
    qtd_success = 0
    total_time = 0
    current_app_index = 0
    total_apps = len(app_pkgs)
    logger.info(f"Worker is about to download {total_apps}.")
    for pkg_name in app_pkgs:
        app_attempt = 0
        success = False
        while not success and app_attempt < 3:
            logger.info(
                f"Initiated download: {pkg_name}")
            start_time = time.time()
            try:
                success, msg = app_downloader.download_app(pkg_name)
                end_time = time.time()
                duration = end_time - start_time
                downloader_log.log_app_downloaded(package_name=pkg_name,
                                                  success=success,
                                                  summary_msg=msg,
                                                  stdout=None, stderr=None,
                                                  traceback_exception=None,
                                                  attempt_index=app_attempt,
                                                  total_secs=duration)
                logger.info(
                    f"Download finished for App: {pkg_name}, Duration: {duration}s")
                if success:
                    qtd_success = qtd_success + 1
            except Exception:
                tb_exception = traceback.format_exc()
                end_time = time.time()
                duration = end_time - start_time
                downloader_log.log_app_downloaded(package_name=pkg_name,
                                                  success=False,
                                                  summary_msg="download failed",
                                                  stdout=None, stderr=None,
                                                  traceback_exception=tb_exception,
                                                  attempt_index=app_attempt,
                                                  total_secs=duration)
                logger.info(
                    f"Download failed for App: {pkg_name}, Duration: {duration}s")
                logger.warning(tb_exception)
            total_time = total_time + duration
            time_spent_so_far = total_time
            average_time = time_spent_so_far / (current_app_index + 1)
            estimated_time_to_finish = average_time * (total_apps - (current_app_index + 1))
            logger.info(
                f"Current app index {current_app_index}. "
                f"Time so far {time_spent_so_far} seconds. "
                f"Time to finish {estimated_time_to_finish}s or {estimated_time_to_finish / 60.0} "
                f"minutes or {estimated_time_to_finish / (60.0 * 60.0)} hours. "
                f"QTD success so far: {qtd_success}, QTD failed so far: {current_app_index+1-qtd_success} "
                f"Avg time per item {average_time} seconds. ")
            logger.info("--------------------------")
            app_attempt = app_attempt + 1
        current_app_index = current_app_index + 1
    return f"Worker downloaded {len(app_pkgs)} and {qtd_success} completed successfully while {len(app_pkgs) - qtd_success} failed"


class DeviceAppsDownloader:

    def __init__(self, config_dir: str = None, output_dir: str = None,
                 device_pool: DevicePool = None, apps=None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.apps = apps
        self.device_pool = device_pool
        self.output_dir = output_dir
        sql_post_config_file = os.path.join(config_dir, 'config', 'apps_downloader_db.sql')
        self.downloader_log = AppDownloaderLog(log_dir=self.output_dir,
                                               sql_post_config_file=sql_post_config_file)

    def execute(self):
        pool_size = self.device_pool.get_size()
        if pool_size == 0:
            raise RuntimeError(f"Can't check any app if the device pool is empty")
        worker_count = max(1, pool_size // 1)
        splits = utils.split_array(self.apps, worker_count)
        results = []
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = []
            for k in splits:
                apps = splits[k]
                gp_downloader = GooglePlayAppDownloader(device_pool=self.device_pool, output_dir=self.output_dir,
                                                        downloader_log=self.downloader_log)
                futures.append(executor.submit(worker, apps, gp_downloader, self.downloader_log))
            for future in as_completed(futures):
                result = future.result()
                print(result)
                results.append(result)
        for item in results:
            print(item)
        self.logger.info("closing logs")
        self.downloader_log.close_logs()
        self.logger.info("completed")
        self.device_pool.shutdown()
        exit(0)
