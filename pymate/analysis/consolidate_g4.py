import hashlib
import os
import sqlite3
from pymate.utils import fs_utils, utils
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from screeninfo import get_monitors
from pymate.csv_logger.CSVLogger import CSVLogger
from pymate.csv_logger.CSVToSQLite import CSVToSQLite
from pymate.csv_logger.SQLiteDBFastLogger import SQLiteDBFastLogger
from pymate.device_observer.logcat_observer import LogcatState
from pymate.analysis.baseline import HealthCheck, HealthCheckIteration, find_databases_with_tags, \
    compare_baseline_with_iterations, save_comparison_iterations
from pymate.analysis.sqlite_helper import execute_query
from pymate.analysis.baseline import create_baseline_from_iterations, load_health_check_from_baseline_db
import shutil
import ast
import csv


def find_apps(database, maker, classification, query, collector = None):
    # query =
    items = execute_query(db_path=database, query=query)
    for item in items:
        collector.append([maker, classification, item[0]])


def find_all_apps(database, maker, healthy, faulty, incompatible):
    find_apps(database, maker, "healthy", "select * from vw_healthy_compatible_apps", healthy)
    find_apps(database, maker, "faulty",
              "select * from vw_faulty_apps", faulty
              )
    find_apps(database, maker, "faulty",
              "select * from vw_health_incompatible_apps", incompatible
              )


def save_array_to_csv(file_path: str, data: list, header: list):
    with open(file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(data)


def main():
    output_dir = "I:\\InstruMate\\g4_consolidated_v2"
    healthy = []
    faulty = []
    incompatible = []
    androlog = "H:\\InstruMate\\InstrumateAnalysis\\g4_variant_comparisons_androlog_v3\\main.db"
    acvtool = "H:\\InstruMate\\InstrumateAnalysis\\g4_variant_comparisons_acvtool\\main.db"
    aspectj_e = "I:\\InstruMate\\g4_variant_comparisons_aspectj_apkeditor\\main.db"
    aspectj_a = "I:\\InstruMate\\g4_variant_comparisons_aspectj_apktool\\main.db"
    frida = "I:\\InstruMate\\g4_variant_comparisons_frida\\main.db"
    find_all_apps(androlog, 'androlog', healthy, faulty, incompatible)
    find_all_apps(acvtool, 'acvtool', healthy, faulty, incompatible)
    find_all_apps(aspectj_a, 'aspectj_a', healthy, faulty, incompatible)
    find_all_apps(aspectj_e, 'aspectj_e', healthy, faulty, incompatible)
    find_all_apps(frida, 'frida', healthy, faulty, incompatible)
    if os.path.exists(output_dir):
        fs_utils.destroy_dir_files(output_dir)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    header = ["maker", "classification", "package_name"]
    save_array_to_csv(os.path.join(output_dir, "healthy_apps.csv"), healthy, header)
    save_array_to_csv(os.path.join(output_dir, "faulty_apps.csv"), faulty, header)
    save_array_to_csv(os.path.join(output_dir, "incompatible_apps.csv"), incompatible, header)










if __name__ == "__main__":
    main()