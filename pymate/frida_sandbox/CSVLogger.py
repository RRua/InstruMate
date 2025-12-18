import csv
import json
import os
import re
import json
from datetime import datetime
from pymate.frida_sandbox import JsonToColumnsConverter


class CSVLogger:
    def __init__(self, basedir, filename, columns_converter: JsonToColumnsConverter):
        self.basedir = basedir
        self.filename = filename
        self.file_path = os.path.join(basedir, filename)
        self.is_open = False
        self.columns_converter = columns_converter
        self.file = None
        self.csv_writer = None
        
    def json_to_columns(self, json_obj, is_header=False):
        if is_header:
            return self.columns_converter.get_header()
        else:
            return self.columns_converter.get_values(json_obj)
    
    def open_log(self, json_obj):
        header = self.json_to_columns(json_obj, True)
        data = self.json_to_columns(json_obj, False)
        self.file = open(self.file_path, "a", newline='', encoding='utf-8')
        self.csv_writer = csv.writer(self.file)
        self.csv_writer.writerow(header)
        self.csv_writer.writerow(data)
        self.is_open = True
        return data

    def append_log(self, json_obj):
        if not self.is_open:
            raise Exception("File is closed")
        data = self.json_to_columns(json_obj, False)
        self.csv_writer.writerow(data)
        return data
    
    def close_log(self):
        if not self.is_open:
            raise Exception("File is closed")
        self.file.flush()
        self.file.close()
        self.is_open = False
