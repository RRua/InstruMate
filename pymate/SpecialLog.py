import os
from datetime import datetime
import logging
import csv


class SpecialLog:

    def __init__(self, base_dir, tag):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.base_dir = base_dir
        self.tag = tag
        self.start_times = {}
        fd = open(
            os.path.join(base_dir, f"{tag}.csv"), 'w+',
            encoding='utf8',
            newline='\n')
        self.csv_writer = csv.writer(fd)
        self.console = open(
            os.path.join(base_dir, f"{tag}-console.log"), 'w+',
            encoding='utf8',
            newline='\n')

    def begin_timed_operation(self, qualifier: str = "None"):
        self.start_times[qualifier] = datetime.now()

    def _get_start_time(self, qualifier: str = "None"):
        return self.start_times[qualifier]

    def end_timed_operation(self, msg="", qualifier: str = "None", extra_data=[]):
        start_time = self._get_start_time(qualifier)
        end_time = datetime.now()
        total_secs = (end_time - start_time).total_seconds()
        final_data = [msg, qualifier, start_time, end_time, total_secs] + extra_data
        q_fmt = f"({qualifier})" if qualifier is not None else ""
        msg_fmt = f"TIMED OPERATION{q_fmt}:{msg} took {total_secs} seconds\n"
        self.logger.debug(msg_fmt)
        self.console.write(msg)
        self.console.flush()
        self.csv_writer.writerow(final_data)
        self.begin_timed_operation(qualifier)
