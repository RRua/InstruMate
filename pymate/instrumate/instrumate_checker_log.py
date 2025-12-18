from pymate.common.app import App
from pymate.csv_logger.SQLiteDBFastLogger import SQLiteDBFastLogger


class InstrumateCheckerLog:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(InstrumateCheckerLog, cls).__new__(cls)
        return cls._instance

    def __init__(self, log_dir: str = None, sql_post_config_file: str = None):
        if not hasattr(self, 'initialized'):
            import logging
            self.logger = logging.getLogger(self.__class__.__name__)
            self.initialized = True
            self.log_dir = log_dir
            self.sql_post_config_file = sql_post_config_file
            self.sqlite_csv_logger = SQLiteDBFastLogger(basedir=log_dir, db_file_name="instrumate_checker_log.db",
                                                        thread_safe=True)
            base_data = [
                "package_name", "app_version", "app_id", "is_variant",
                "variant_maker_tag", "variant_flag", "variant_flag_str",
                "level_flag", "level_flag_str"
            ]
            commands_data = [
                "action",
                "success", "stdout", "stderr", "traceback_exception", "attempt_index",
                "total_secs"
            ]
            view_state_component_data = [
                "signature", "android_class",
                "package", "uniqueId", "parentUniqueId",
                "resourceID", "contentDesc", "text",
                "checkable", "checked", "clickable",
                "enabled", "focusable", "focused",
                "scrollable", "visibility", "password", "selected"
            ]
            view_state_action_units = ["view_signature", "view_id", "cls", "pkg", "label", "type"]
            logcat_messages = ["month", "day", "time", "pid", "tid", "level", "pkg_name", "msg"]
            app_exceptions = ["captured_exception_name"]
            app_exception_sites = ["exception_name", "method_signature", "detail", "exception_index", "raw_msg"]
            instrumate_checker_result = [
                "procedure_completed",
                "failure_reason",
                "traceback_exception",
                "total_secs"
            ]
            running_activities = [
                "activity_name"
            ]
            self.sqlite_csv_logger.add_logger("instrumate_checker_commands", base_data + commands_data)
            self.sqlite_csv_logger.add_logger("view_state_component_data", base_data + view_state_component_data)
            self.sqlite_csv_logger.add_logger("view_state_action_units", base_data + view_state_action_units)
            self.sqlite_csv_logger.add_logger("logcat_messages", base_data + logcat_messages)
            self.sqlite_csv_logger.add_logger("instrumate_checker_result", base_data + instrumate_checker_result)
            self.sqlite_csv_logger.add_logger("app_exceptions", base_data + app_exceptions)
            self.sqlite_csv_logger.add_logger("app_exception_sites", base_data + app_exception_sites)
            self.sqlite_csv_logger.add_logger("running_activities", base_data + running_activities)

    def log_command_execution(self, app: App, action: str, success=True, stdout=None, stderr=None,
                              traceback_exception=None, attempt_index=0, total_secs=0):
        data = self.sqlite_csv_logger.log_data("instrumate_checker_commands", [
            app.get_package_name(),
            app.get_app_version_name(),
            app.get_app_id(),
            app.is_variant(),
            app.get_variant_maker_tag(),
            app.get_variant_bin_features(),
            app.get_variant_feature_labels(),
            app.get_variant_bin_levels(),
            app.get_variant_level_labels(),
            action, success, stdout, stderr,
            traceback_exception, attempt_index, total_secs
        ])
        #self.logger.debug(str(data))

    def log_app_view_state_component(self, app: App, signature, android_class,
                                     package, uniqueId, parentUniqueId,
                                     resourceID, contentDesc, text,
                                     checkable, checked, clickable,
                                     enabled, focusable, focused,
                                     scrollable, visibility, password, selected):
        data = self.sqlite_csv_logger.log_data("view_state_component_data", [
            app.get_package_name(),
            app.get_app_version_name(),
            app.get_app_id(),
            app.is_variant(),
            app.get_variant_maker_tag(),
            app.get_variant_bin_features(),
            app.get_variant_feature_labels(),
            app.get_variant_bin_levels(),
            app.get_variant_level_labels(),
            signature, android_class,
            package, uniqueId, parentUniqueId,
            resourceID, contentDesc, text,
            checkable, checked, clickable,
            enabled, focusable, focused,
            scrollable, visibility, password, selected
        ])
        #self.logger.debug(str(data))

    def log_app_view_state_action_unit(self, app: App, view_signature, view_id, cls, pkg, label, action_type):
        data = self.sqlite_csv_logger.log_data("view_state_action_units", [
            app.get_package_name(),
            app.get_app_version_name(),
            app.get_app_id(),
            app.is_variant(),
            app.get_variant_maker_tag(),
            app.get_variant_bin_features(),
            app.get_variant_feature_labels(),
            app.get_variant_bin_levels(),
            app.get_variant_level_labels(),
            view_signature, view_id, cls, pkg, label, action_type
        ])
        #self.logger.debug(str(data))

    def log_app_logcat_msg(self, app: App, month, day, time, pid, tid, level, pkg_name, msg):
        data = self.sqlite_csv_logger.log_data("logcat_messages", [
            app.get_package_name(),
            app.get_app_version_name(),
            app.get_app_id(),
            app.is_variant(),
            app.get_variant_maker_tag(),
            app.get_variant_bin_features(),
            app.get_variant_feature_labels(),
            app.get_variant_bin_levels(),
            app.get_variant_level_labels(),
            month, day, time, pid, tid, level, pkg_name, msg
        ])
        #self.logger.debug(str(data))

    def log_app_exception(self, app: App, exception_name):
        data = self.sqlite_csv_logger.log_data("app_exceptions", [
            app.get_package_name(),
            app.get_app_version_name(),
            app.get_app_id(),
            app.is_variant(),
            app.get_variant_maker_tag(),
            app.get_variant_bin_features(),
            app.get_variant_feature_labels(),
            app.get_variant_bin_levels(),
            app.get_variant_level_labels(),
            exception_name
        ])
        #self.logger.debug(str(data))

    def log_app_exception_site(self, app: App, exception_name, method_signature, detail, index, raw_msg):
        data = self.sqlite_csv_logger.log_data("app_exception_sites", [
            app.get_package_name(),
            app.get_app_version_name(),
            app.get_app_id(),
            app.is_variant(),
            app.get_variant_maker_tag(),
            app.get_variant_bin_features(),
            app.get_variant_feature_labels(),
            app.get_variant_bin_levels(),
            app.get_variant_level_labels(),
            exception_name,
            method_signature,
            detail,
            index,
            raw_msg
        ])
        #self.logger.debug(str(data))

    def log_app_result(self, app: App, procedure_completed=False, failure_reason=None,
                       traceback_exception=None,
                       total_secs=0):
        data = self.sqlite_csv_logger.log_data("instrumate_checker_result", [
            app.get_package_name(),
            app.get_app_version_name(),
            app.get_app_id(),
            app.is_variant(),
            app.get_variant_maker_tag(),
            app.get_variant_bin_features(),
            app.get_variant_feature_labels(),
            app.get_variant_bin_levels(),
            app.get_variant_level_labels(),
            procedure_completed,
            failure_reason,
            traceback_exception, total_secs
        ])
        #self.logger.debug(str(data))

    def log_running_activity(self, app: App, activity_name):
        data = self.sqlite_csv_logger.log_data("running_activities", [
            app.get_package_name(),
            app.get_app_version_name(),
            app.get_app_id(),
            app.is_variant(),
            app.get_variant_maker_tag(),
            app.get_variant_bin_features(),
            app.get_variant_feature_labels(),
            app.get_variant_bin_levels(),
            app.get_variant_level_labels(),
            activity_name
        ])
        #self.logger.debug(str(data))

    def close_logs(self):
        self.sqlite_csv_logger.close()
        self.sqlite_csv_logger.consolidate_database()
        self.sqlite_csv_logger.exec_post_create(sql_file=self.sql_post_config_file)
