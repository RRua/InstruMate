from pymate.common.command import Command
from pymate.csv_logger.SQLiteDBFastLogger import SQLiteDBFastLogger


class InstruMateLog:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(InstruMateLog, cls).__new__(cls)
        return cls._instance

    def __init__(self, log_dir: str = None, sql_post_config_file: str = None):
        if not hasattr(self, 'initialized'):
            import logging
            self.logger = logging.getLogger(self.__class__.__name__)
            self.initialized = True
            self.log_dir = log_dir
            self.sql_post_config_file = sql_post_config_file
            self.sqlite_csv_logger = SQLiteDBFastLogger(basedir=log_dir, db_file_name="instrumate_log.db")
            self.sqlite_csv_logger.add_logger("static_analyzer_execution", ["static_analyzer_name", "package_name",
                                                                            "base_pkg", "app_id", "app_version",
                                                                            "variant_flag", "variant_flag_str",
                                                                            "level_flag", "level_flag_str",
                                                                            "success",
                                                                            "tb_exception", "total_secs"])
            self.sqlite_csv_logger.add_logger("variant_maker_tool_executions",
                                              ["variant_maker", "variant_maker_tag", "tool_name", "tool_description",
                                               "input_app",
                                               "package_name",
                                               "app_version",
                                               "app_id",
                                               "variant_flag", "variant_flag_str",
                                               "level_flag", "level_flag_str",
                                               "tool_success", "tool_cmd_stdout", "tool_cmd_stderr",
                                               "tool_script_stdout",
                                               "tool_script_stderr",
                                               "tool_traceback_exception",
                                               "tool_total_secs",
                                               "tool_options"])

    def register_generic_logger(self, logger_name, columns):
        if not self.sqlite_csv_logger.has_logger(logger_name):
            self.sqlite_csv_logger.add_logger(logger_name, columns)

    def record_generic_log(self, logger_name, log_data):
        self.sqlite_csv_logger.log_data(logger_name, log_data)

    def log_static_analyzer_execution(self, static_analyzer_name, package_name,
                                      base_pkg, app_id, app_version, variant_flag, variant_flag_str,
                                      level_flag, level_flag_str, success,
                                      tb_exception, total_secs):
        data = self.sqlite_csv_logger.log_data("static_analyzer_execution", [static_analyzer_name, package_name,
                                                                             base_pkg, app_id, app_version,
                                                                             variant_flag, variant_flag_str,
                                                                             level_flag, level_flag_str, success,
                                                                             tb_exception, total_secs])
        self.logger.debug(str(data))

    def log_variant_maker_tool_exec(self, variant_maker, variant_maker_tag, tool_name, tool_description,
                                    input_app,
                                    package_name,
                                    package_version,
                                    app_id,
                                    variant_flag, variant_flag_str,
                                    level_flag, level_flag_str,
                                    tool_success, tool_cmd_stdout, tool_cmd_stderr,
                                    tool_script_stdout,
                                    tool_script_stderr,
                                    tool_traceback_exception,
                                    tool_total_secs,
                                    tool_options):
        data = self.sqlite_csv_logger.log_data("variant_maker_tool_executions",
                                               [variant_maker, variant_maker_tag, tool_name, tool_description,
                                                input_app,
                                                package_name,
                                                package_version,
                                                app_id,
                                                variant_flag, variant_flag_str,
                                                level_flag, level_flag_str,
                                                tool_success, tool_cmd_stdout, tool_cmd_stderr,
                                                tool_script_stdout,
                                                tool_script_stderr,
                                                tool_traceback_exception,
                                                tool_total_secs,
                                                tool_options])
        self.logger.debug(str([variant_maker, tool_name, tool_success]))
        if not tool_success:
            self.logger.debug("cmd stdout:")
            self.logger.debug(tool_cmd_stdout)
            self.logger.debug("cmd stderr")
            self.logger.debug(tool_cmd_stderr)
            self.logger.debug("script stdout")
            self.logger.debug(tool_script_stdout)
            self.logger.debug("script stderr")
            self.logger.debug(tool_script_stderr)

    def close_logs(self):
        self.sqlite_csv_logger.close()
        self.sqlite_csv_logger.consolidate_database()
        self.sqlite_csv_logger.exec_post_create(sql_file=self.sql_post_config_file)