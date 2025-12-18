import os
from loguru import logger
import logging
from androguard.core.apk import APK
from pymate.common.intent import Intent
from pymate.common.app import App
from pymate.instrumate.static_analyzer import StaticAnalyzer


class AndroguardApkAnalyzer(StaticAnalyzer):

    def configure(self, tmp_dir: str = None, output_dir: str = None, tools_dir: str = None, name: str = None,
                  instrumate_log=None):
        super().configure(tmp_dir=tmp_dir, output_dir=output_dir, tools_dir=tools_dir,
                          name="Androguard Static Analyzer",
                          instrumate_log=instrumate_log)
        self.logger = logging.getLogger(self.__class__.__name__)

    def analyze_app(self, app: App):
        # loguru
        logger.remove()
        if self.logger.isEnabledFor(logging.DEBUG):
            logger.add(sink=os.path.join(self.tmp_dir, "loguru.log"), level="DEBUG")
        else:
            logger.add(lambda _: None)
        # loguru
        apk = APK(app.get_base_pkg())
        app.set_package_name(apk.get_package())
        app.set_min_sdk_version(apk.get_min_sdk_version())
        app.set_max_sdk_version(apk.get_max_sdk_version())
        app.set_target_sdk_version(apk.get_target_sdk_version())
        app.set_app_version_name(apk.get_androidversion_name())
        app.set_app_version_code(apk.get_androidversion_code())
        app.set_app_implied_permissions(apk.get_uses_implied_permission_list())
        app.set_services(apk.get_services())
        app.set_main_activity(apk.get_main_activity())
        app.set_permissions(apk.get_permissions())
        app.set_activities(apk.get_activities())
        app.set_features(apk.get_features())
        app.set_possible_broadcasts(AndroguardApkAnalyzer.get_possible_broadcasts(apk))
        try:
            app.set_app_name = apk.get_app_name()
        except:
            self.logger.warning(f"AndroGuard failed to read resources from APK {app.get_base_pkg()}")
        try:
            app.set_app_icon(apk.get_app_icon())
        except:
            self.logger.warning(f"Androguard failed to identify the app icon {app.get_base_pkg()}")

    @staticmethod
    def get_possible_broadcasts(apk: APK):
        possible_broadcasts = list()
        for receiver in apk.get_receivers():
            intent_filters = apk.get_intent_filters('receiver', receiver)
            actions = intent_filters['action'] if 'action' in intent_filters else []
            categories = intent_filters['category'] if 'category' in intent_filters else []
            categories.append(None)
            for action in actions:
                for category in categories:
                    intent = Intent(prefix='broadcast', action=action, category=category)
                    possible_broadcasts.append(intent.to_dict())
        return possible_broadcasts

    def save_analysis(self, app: App):
        self.register_log(
            "app_info",
            ["min_sdk", "max_sdk", "target_sdk", "main_activity", "version_name", "version_code", "base_pkg_file",
             "splits", "app_size"]
        )
        app_size = -1
        base_size = -1
        if os.path.isfile(app.get_base_pkg()):
            base_size = os.path.getsize(app.get_base_pkg())
            app_size = app_size + base_size
        for split in app.get_split_pkgs():
            if os.path.isfile(split):
                app_size = app_size + os.path.getsize(split)
        self.record_log("app_info",
                        app,
                        [app.get_min_sdk_version(), app.get_max_sdk_version(), app.get_target_sdk_version(),
                         app.get_main_activity(), app.get_app_version_name(), app.get_app_version_code(),
                         app.get_base_pkg(),
                         ",".join(app.get_split_pkgs()) if app.has_split_pkgs() else None,
                         app_size])

        self.register_log(
            "apk_info",
            ["apk_file", "apk_size"]
        )
        self.record_log("apk_info",
                        app, [app.get_base_pkg(), base_size])
        for split in app.get_split_pkgs():
            split_size = -1
            if os.path.isfile(split):
                split_size = os.path.getsize(split)
            self.record_log("apk_info",
                            app, [split, split_size])

        self.register_log(
            "app_permissions",
            ["permission_name"]
        )
        for permission in app.get_permissions():
            self.record_log("app_permissions",
                            app, [permission])
        self.register_log(
            "app_implied_permissions",
            ["permission_name"]
        )
        for permission in app.get_app_implied_permissions():
            self.record_log("app_implied_permissions",
                            app, [permission])
        self.register_log(
            "app_services",
            ["service_name"]
        )
        for service_name in app.get_services():
            self.record_log("app_services",
                            app, [service_name])
        self.register_log(
            "app_activities",
            ["activity_name"]
        )
        for activity_name in app.get_activities():
            self.record_log("app_activities",
                            app, [activity_name])
        self.register_log(
            "app_features",
            ["feature_name"]
        )
        for feature_name in app.get_features():
            self.record_log("app_activities",
                            app, [feature_name])
        self.register_log(
            "app_possible_broadcasts",
            ["event_type", "prefix", "action", "cmd"]
        )
        for broadcast_dict in app.get_possible_broadcasts():
            self.record_log("app_possible_broadcasts",
                            app, [broadcast_dict.get("event_type", None),
                                  broadcast_dict.get("prefix", None),
                                  broadcast_dict.get("action", None),
                                  broadcast_dict.get("cmd", None)])
