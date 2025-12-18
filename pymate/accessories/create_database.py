import logging
from pymate.csv_logger.SQLiteDBFastLogger import SQLiteDBFastLogger

class CreateDatabase:
    def __init__(self, log_dir, sql_post_config_file, database_name):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.log_dir = log_dir
        self.sql_post_config_file = sql_post_config_file
        self.sqlite_csv_logger = SQLiteDBFastLogger(basedir=log_dir, db_file_name=database_name,
                                                    thread_safe=True)


    def create_database(self):
        self.sqlite_csv_logger.consolidate_database()
        self.sqlite_csv_logger.exec_post_create(sql_file=self.sql_post_config_file)