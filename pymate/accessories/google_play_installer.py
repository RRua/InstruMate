import logging
from pymate.device_link import DeviceLink


class GooglePlayInstaller:
    def __init__(self, pkg_ids, uninstall_installed=False, update_version=False, open_app=False, gui_timeout=2,
                 install_timeout=5,
                 retry_failed_apps_count=3,
                 device_link: DeviceLink = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.pkg_ids = pkg_ids
        self.uninstall_installed = uninstall_installed
        self.update_version = update_version
        self.open_app = open_app
        self.gui_timeout = gui_timeout
        self.install_timeout = install_timeout
        self.retry_failed_apps_count = retry_failed_apps_count
        self.device_link = device_link

    def install_pkgs(self):
        self.logger.info(f"Installing {len(self.pkg_ids)} apps")
        failed_apps = self.device_link.install_apps_from_google_play(pkg_list=self.pkg_ids,
                                                                     uninstall_installed=self.uninstall_installed,
                                                                     update_version=self.update_version,
                                                                     open_app=self.open_app,
                                                                     gui_timeout=self.gui_timeout,
                                                                     install_timeout=self.install_timeout)
        self.logger.info(f"Installation failed for {len(failed_apps)} apps")
        retry_num = 1
        while retry_num < self.retry_failed_apps_count:
            self.logger.debug(f"Apps to retry {failed_apps}")
            failed_apps = self.device_link.install_apps_from_google_play(pkg_list=failed_apps,
                                                                         uninstall_installed=self.uninstall_installed,
                                                                         update_version=self.update_version,
                                                                         open_app=self.open_app,
                                                                         gui_timeout=self.gui_timeout,
                                                                         install_timeout=self.install_timeout)
            self.logger.info(f"Installation failed for {len(failed_apps)} apps")
            retry_num = retry_num + 1
            if len(failed_apps) == 0:
                break
