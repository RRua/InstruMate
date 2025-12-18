from pymate.csv_logger.CSVLogger import CSVLogger
from pymate.csv_logger.CSVToSQLite import CSVToSQLite


class SQLiteDBFastLogger:
    def __init__(self, basedir, db_file_name="main.db", thread_safe=False):
        self.basedir = basedir
        self.db_file_name = db_file_name
        self.loggers = {}
        self.csv_to_sqlite = None
        self.thread_safe = thread_safe

    def add_logger(self, table_name, column_names):
        self.loggers[table_name] = CSVLogger(basedir=self.basedir, filename=f"{table_name}.csv",
                                             thread_safe=self.thread_safe)
        self.loggers[table_name].open_log(column_names)

    def has_logger(self, table_name):
        if table_name in self.loggers:
            return True
        return False

    def log_data(self, table_name, row_data):
        return self.loggers[table_name].append_log(row_data)

    def consolidate_database(self):
        self.csv_to_sqlite = CSVToSQLite(dest_dir=self.basedir, db_file_name=self.db_file_name)
        self.csv_to_sqlite.import_csv_dir_into_database(self.basedir)

    def exec_post_create(self, sql_file):
        if self.csv_to_sqlite:
            self.csv_to_sqlite.execute_sql_file(sql_file)

    def close(self):
        for table_name in self.loggers:
            self.loggers[table_name].close_log()


def main():
    logger = SQLiteDBFastLogger(basedir='I:\git\\forensicmate-static-analysis\\output')
    logger.consolidate_database()


if __name__ == "__main__":
    main()
