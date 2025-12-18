from pymate.csv_logger.SQLiteDBFastLogger import SQLiteDBFastLogger


class AppDownloaderLog:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AppDownloaderLog, cls).__new__(cls)
        return cls._instance

    def __init__(self, log_dir: str = None, sql_post_config_file: str = None):
        if not hasattr(self, 'initialized'):
            import logging
            self.logger = logging.getLogger(self.__class__.__name__)
            self.initialized = True
            self.log_dir = log_dir
            self.sql_post_config_file = sql_post_config_file
            self.sqlite_csv_logger = SQLiteDBFastLogger(basedir=log_dir, db_file_name="app_downloader_log.db",
                                                        thread_safe=True)
            base_data = [
                "package_name",
                "summary_msg",
                "success",
                "attempt_index",
                "stdout", "stderr",
                "traceback_exception",
                "total_secs",
            ]
            self.sqlite_csv_logger.add_logger("downloader_action", base_data)
            self.sqlite_csv_logger.add_logger("app_downloaded", base_data)

    def log_app_downloaded(self, package_name,
                           summary_msg,
                           success,
                           attempt_index,
                           stdout, stderr,
                           traceback_exception,
                           total_secs):
        data = self.sqlite_csv_logger.log_data("app_downloaded", [
            package_name,
            summary_msg,
            success,
            attempt_index,
            stdout, stderr,
            traceback_exception,
            total_secs
        ])
        self.logger.debug(str(data))

    def log_downloader_action(self, package_name,
                              summary_msg,
                              success,
                              attempt_index,
                              stdout, stderr,
                              traceback_exception,
                              total_secs):
        data = self.sqlite_csv_logger.log_data("downloader_action", [
            package_name,
            summary_msg,
            success,
            attempt_index,
            stdout, stderr,
            traceback_exception,
            total_secs
        ])
        self.logger.debug(str(data))

    def close_logs(self):
        self.sqlite_csv_logger.close()
        self.sqlite_csv_logger.consolidate_database()
        self.sqlite_csv_logger.exec_post_create(sql_file=self.sql_post_config_file)
