import threading
import csv
import os
import traceback


class CSVLogger:
    def __init__(self, basedir, filename, append_if_exists = True, thread_safe=False):
        self.basedir = basedir
        self.filename = filename
        self.file_path = os.path.join(basedir, filename)
        self.is_open = False
        self.file = None
        self.csv_writer = None
        self.append_if_exists = append_if_exists
        self.dict_based_header = None
        self.thread_safe = thread_safe
        if self.thread_safe:
            self.lock = threading.Lock()

    def open_log_with_dict(self, data_dict):
        try:
            if self.thread_safe:
                self.lock.acquire()
            if self.is_open:
                raise RuntimeError("log already open")
            sorted_keys = sorted(data_dict.keys())
            sorted_values = [data_dict[key] for key in sorted_keys]
            self.dict_based_header = sorted_keys
            self.open_log(header=sorted_keys, data=sorted_values)
        finally:
            if self.thread_safe:
                self.lock.release()

    def append_dict_log(self, data_dict):
        try:
            if self.thread_safe:
                self.lock.acquire()
            if self.dict_based_header is None:
                raise RuntimeError('Illegal state: must be opened with a dict')
            sorted_values = [data_dict[key] for key in self.dict_based_header]
            self.append_log(sorted_values)
        finally:
            if self.thread_safe:
                self.lock.release()

    def open_log(self, header, data=None):
        try:
            if self.thread_safe:
                self.lock.acquire()
            if os.path.exists(self.file_path):
                if self.append_if_exists:
                    self.file = open(self.file_path, "a", newline='', encoding='utf-8')
                    self.csv_writer = csv.writer(self.file, escapechar='\\', quotechar='"')
                else:
                    raise RuntimeError('File already exists. Remove or set append_if_exists to True')
            else:
                self.file = open(self.file_path, "w", newline='', encoding='utf-8')
                self.csv_writer = csv.writer(self.file, escapechar='\\', quotechar='"')
                self.csv_writer.writerow(header)
            if data is not None:
                self.csv_writer.writerow(data)
            self.is_open = True
            return data
        finally:
            if self.thread_safe:
                self.lock.release()

    def append_log(self, data):
        try:
            if self.thread_safe:
                self.lock.acquire()
            if not self.is_open:
                raise Exception("File is closed")
            self.csv_writer.writerow(data)
            return data
        finally:
            if self.thread_safe:
                self.lock.release()

    def close_log(self):
        try:
            if self.thread_safe:
                self.lock.acquire()
            if not self.is_open:
                raise Exception("File is closed")
            try:
                self.file.flush()
                self.file.close()
            except Exception as e:
                print(f"An error occurred on close - CSVClogger: {e}")
                traceback.print_exc()
            self.is_open = False
        finally:
            if self.thread_safe:
                self.lock.release()
