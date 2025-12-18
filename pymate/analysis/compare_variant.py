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


def copy_matching_dir_to_dest(input_dir, output_dir, find_strings):
    if not os.path.exists(input_dir):
        print(f"Input directory '{input_dir}' does not exist.")
        return
    os.makedirs(output_dir, exist_ok=True)
    for item in os.listdir(input_dir):
        item_path = os.path.join(input_dir, item)
        if os.path.isdir(item_path):
            if any(substring in item for substring in find_strings):
                target_path = os.path.join(output_dir, item)
                try:
                    # Merge the directory into the target path
                    if not os.path.exists(target_path):
                        shutil.copytree(item_path, target_path)
                    else:
                        for root, dirs, files in os.walk(item_path):
                            relative_path = os.path.relpath(root, item_path)
                            dest_root = os.path.join(target_path, relative_path)
                            os.makedirs(dest_root, exist_ok=True)
                            for file in files:
                                src_file = os.path.join(root, file)
                                dest_file = os.path.join(dest_root, file)
                                shutil.copy2(src_file, dest_file)
                    print(f"Merged '{item_path}' into '{target_path}'")
                except Exception as e:
                    print(f"Error merging '{item_path}' into '{target_path}': {e}")


def copy_faulty_to_output_dir(database, input_dir, output_dir):
    query_pkg_names = "select package_name from vw_faulty_apps"
    pkg_names = [item[0] for item in execute_query(database, query_pkg_names)]
    copy_matching_dir_to_dest(input_dir, output_dir, pkg_names)


def copy_healthy_compatible_to_output_dir(database, input_dir, output_dir):
    query = "select package_name, app_id from vw_healthy_compatible_variants"
    names = [f"{item[0]}-{item[1]}" for item in execute_query(database, query)]
    copy_matching_dir_to_dest(input_dir, output_dir, names)


def copy_healthy_incompatible_to_output_dir(database, input_dir, output_dir):
    query = "select package_name, app_id from vw_healthy_incompatible_variants"
    names = [f"{item[0]}-{item[1]}" for item in execute_query(database, query)]
    copy_matching_dir_to_dest(input_dir, output_dir, names)

def compare_g1():
    output_dir = "H:\\InstruMate\\InstrumateAnalysis\\g1_variant_comparisons\\"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    else:
        fs_utils.destroy_dir_files(output_dir)
        os.makedirs(output_dir)
    baseline_db = "H:\\InstruMate\\InstrumateAnalysis\\baseline\\main.db"
    g1_app_info_db = "H:\\InstruMate\\InstrumateAnalysis\\g1_signature\\instrumate_log.db"
    query_packages = f"select distinct(package_name) from hc_iteration_views"
    package_names = [item[0] for item in execute_query(baseline_db, query_packages)]
    baseline = load_health_check_from_baseline_db(baseline_db=baseline_db, package_names=package_names,
                                                  iteration_number=199)
    tags = [['dataset-hc-g1', 0, 3]]
    databases, success_apps, failed_databases = find_databases_with_tags(tags,
                                                                         "H:\\InstruMate\\InstrumateAnalysis\\g1_signature\\hc-g1",
                                                                         forced_apps_exclusion=[],
                                                                         discard_db_with_failures=False)
    databases_to_check = [databases[key]["database"] for key in databases]
    iterations = compare_baseline_with_iterations(baseline=baseline, databases_to_check=databases_to_check,
                                                  dataset_packages=package_names,
                                                  output_dir=output_dir, copy_to_output=True)

    save_comparison_iterations(app_info_db=g1_app_info_db, output_dir=output_dir, iterations=iterations,
                               expected_packages=package_names, databases=databases_to_check)

    created_database = os.path.join(output_dir, "main.db")
    if os.path.exists(created_database):
        for db_to_check in databases_to_check:
            input_dir = Path(db_to_check).parent
            copy_faulty_to_output_dir(created_database, input_dir, os.path.join(output_dir, "faulty-apps"))
            copy_healthy_incompatible_to_output_dir(created_database, input_dir,
                                                    os.path.join(output_dir, "healthy-incompatible"))
            copy_healthy_compatible_to_output_dir(created_database, input_dir,
                                                  os.path.join(output_dir, "healthy-compatible"))


def compare_g1_again():
    output_dir = "H:\\InstruMate\\InstrumateAnalysis\\g1_variant_comparisons_again\\"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    else:
        fs_utils.destroy_dir_files(output_dir)
        os.makedirs(output_dir)
    baseline_db = "H:\\InstruMate\\InstrumateAnalysis\\baseline\\main.db"
    g1_app_info_db = "H:\\InstruMate\\InstrumateAnalysis\\g1_signature\\instrumate_log.db"
    query_packages = f"select distinct(package_name) from hc_iteration_views"
    package_names = [item[0] for item in execute_query(baseline_db, query_packages)]
    baseline = load_health_check_from_baseline_db(baseline_db=baseline_db, package_names=package_names,
                                                  iteration_number=199)
    tags = [['dataset-hc-g1', 0, 3]]
    databases, success_apps, failed_databases = find_databases_with_tags(tags,
                                                                         "H:\\InstruMate\\InstrumateAnalysis\\g1_signature\\hc-g1",
                                                                         forced_apps_exclusion=[],
                                                                         discard_db_with_failures=False)
    databases_to_check = [databases[key]["database"] for key in databases]
    iterations = compare_baseline_with_iterations(baseline=baseline, databases_to_check=databases_to_check,
                                                  dataset_packages=package_names,
                                                  output_dir=output_dir, copy_to_output=True)

    save_comparison_iterations(app_info_db=g1_app_info_db, output_dir=output_dir, iterations=iterations,
                               expected_packages=package_names, databases=databases_to_check)

    created_database = os.path.join(output_dir, "main.db")
    if os.path.exists(created_database):
        for db_to_check in databases_to_check:
            input_dir = Path(db_to_check).parent
            copy_faulty_to_output_dir(created_database, input_dir, os.path.join(output_dir, "faulty-apps"))
            copy_healthy_incompatible_to_output_dir(created_database, input_dir,
                                                    os.path.join(output_dir, "healthy-incompatible"))
            copy_healthy_compatible_to_output_dir(created_database, input_dir,
                                                  os.path.join(output_dir, "healthy-compatible"))

def compare_g2():
    output_dir = "H:\\InstruMate\\InstrumateAnalysis\\g2_variant_comparisons_v3\\"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    else:
        fs_utils.destroy_dir_files(output_dir)
        os.makedirs(output_dir)
    baseline_db = "H:\\InstruMate\\InstrumateAnalysis\\baseline\\main.db"
    app_info_db = "H:\\InstruMate\\InstrumateAnalysis\\g2_manifest\\instrumate_log.db"
    query_packages = f"select distinct(package_name) from hc_iteration_views"
    package_names = [item[0] for item in execute_query(baseline_db, query_packages)]
    baseline = load_health_check_from_baseline_db(baseline_db=baseline_db, package_names=package_names,
                                                  iteration_number=199)
    tags = [['dataset-hc-g2-leo', 0, 3]]
    databases, success_apps, failed_databases = find_databases_with_tags(tags,
                                                                         "H:\\InstruMate\\InstrumateAnalysis\\g2_manifest\\hc_g2",
                                                                         forced_apps_exclusion=[],
                                                                         discard_db_with_failures=False)
    databases_to_check = [databases[key]["database"] for key in databases]
    iterations = compare_baseline_with_iterations(baseline=baseline, databases_to_check=databases_to_check,
                                                  dataset_packages=package_names,
                                                  output_dir=output_dir, copy_to_output=True)

    save_comparison_iterations(app_info_db=app_info_db, output_dir=output_dir, iterations=iterations,
                               expected_packages=package_names, databases=databases_to_check)

    created_database = os.path.join(output_dir, "main.db")
    if os.path.exists(created_database):
        for db_to_check in databases_to_check:
            input_dir = Path(db_to_check).parent
            copy_faulty_to_output_dir(created_database, input_dir, os.path.join(output_dir, "faulty-apps"))
            copy_healthy_incompatible_to_output_dir(created_database, input_dir,
                                                    os.path.join(output_dir, "healthy-incompatible"))
            copy_healthy_compatible_to_output_dir(created_database, input_dir,
                                                  os.path.join(output_dir, "healthy-compatible"))


def compare_g3():
    output_dir = "H:\\InstruMate\\InstrumateAnalysis\\g3_variant_comparisons_v1\\"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    else:
        fs_utils.destroy_dir_files(output_dir)
        os.makedirs(output_dir)
    baseline_db = "H:\\InstruMate\\InstrumateAnalysis\\baseline\\main.db"
    app_info_db = "H:\\InstruMate\\InstrumateAnalysis\\g3_resources\\instrumate_log.db"
    query_packages = f"select distinct(package_name) from hc_iteration_views"
    package_names = [item[0] for item in execute_query(baseline_db, query_packages)]
    baseline = load_health_check_from_baseline_db(baseline_db=baseline_db, package_names=package_names,
                                                  iteration_number=199)
    tags = [['dataset-hc-g3', 0, 3]]
    databases, success_apps, failed_databases = find_databases_with_tags(tags,
                                                                         "H:\\InstruMate\\InstrumateAnalysis\\g3_resources\\hc-g3",
                                                                         forced_apps_exclusion=[],
                                                                         discard_db_with_failures=False)
    databases_to_check = [databases[key]["database"] for key in databases]
    iterations = compare_baseline_with_iterations(baseline=baseline, databases_to_check=databases_to_check,
                                                  dataset_packages=package_names,
                                                  output_dir=output_dir, copy_to_output=True)

    save_comparison_iterations(app_info_db=app_info_db, output_dir=output_dir, iterations=iterations,
                               expected_packages=package_names, databases=databases_to_check)

    created_database = os.path.join(output_dir, "main.db")
    if os.path.exists(created_database):
        for db_to_check in databases_to_check:
            input_dir = Path(db_to_check).parent
            copy_faulty_to_output_dir(created_database, input_dir, os.path.join(output_dir, "faulty-apps"))
            copy_healthy_incompatible_to_output_dir(created_database, input_dir,
                                                    os.path.join(output_dir, "healthy-incompatible"))
            copy_healthy_compatible_to_output_dir(created_database, input_dir,
                                                  os.path.join(output_dir, "healthy-compatible"))


def compare_g4_androlog():
    output_dir = "H:\\InstruMate\\InstrumateAnalysis\\g4_variant_comparisons_androlog_v3\\"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    else:
        fs_utils.destroy_dir_files(output_dir)
        os.makedirs(output_dir)
    baseline_db = "H:\\InstruMate\\InstrumateAnalysis\\baseline\\main.db"
    app_info_db = "H:\\InstruMate\\InstrumateAnalysis\\g4_androlog\\instrumate_log.db"
    query_packages = f"select distinct(package_name) from hc_iteration_views"
    package_names = [item[0] for item in execute_query(baseline_db, query_packages)]
    baseline = load_health_check_from_baseline_db(baseline_db=baseline_db, package_names=package_names,
                                                  iteration_number=199)
    tags = [['dataset-hc-g4-androlog', 0, 3]]
    databases, success_apps, failed_databases = find_databases_with_tags(tags,
                                                                         "H:\\InstruMate\\InstrumateAnalysis\\g4_androlog\\hc-g4-andrologv3",
                                                                         forced_apps_exclusion=[],
                                                                         discard_db_with_failures=False)
    databases_to_check = [databases[key]["database"] for key in databases]
    iterations = compare_baseline_with_iterations(baseline=baseline, databases_to_check=databases_to_check,
                                                  dataset_packages=package_names,
                                                  output_dir=output_dir, copy_to_output=True)

    save_comparison_iterations(app_info_db=app_info_db, output_dir=output_dir, iterations=iterations,
                               expected_packages=package_names, databases=databases_to_check)

    created_database = os.path.join(output_dir, "main.db")
    if os.path.exists(created_database):
        for db_to_check in databases_to_check:
            input_dir = Path(db_to_check).parent
            copy_faulty_to_output_dir(created_database, input_dir, os.path.join(output_dir, "faulty-apps"))
            copy_healthy_incompatible_to_output_dir(created_database, input_dir,
                                                    os.path.join(output_dir, "healthy-incompatible"))
            copy_healthy_compatible_to_output_dir(created_database, input_dir,
                                                  os.path.join(output_dir, "healthy-compatible"))

def compare_g4_acvtool():
    output_dir = "H:\\InstruMate\\InstrumateAnalysis\\g4_variant_comparisons_acvtool\\"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    else:
        fs_utils.destroy_dir_files(output_dir)
        os.makedirs(output_dir)
    baseline_db = "H:\\InstruMate\\InstrumateAnalysis\\baseline\\main.db"
    app_info_db = "H:\\InstruMate\\InstrumateAnalysis\\g4_acvtool\\instrumate_log.db"
    query_packages = f"select distinct(package_name) from hc_iteration_views"
    package_names = [item[0] for item in execute_query(baseline_db, query_packages)]
    baseline = load_health_check_from_baseline_db(baseline_db=baseline_db, package_names=package_names,
                                                  iteration_number=199)
    tags = [['dataset-hc-g4-acvtool', 0, 3]]
    databases, success_apps, failed_databases = find_databases_with_tags(tags,
                                                                         "H:\\InstruMate\\InstrumateAnalysis\\g4_acvtool\\hc",
                                                                         forced_apps_exclusion=[],
                                                                         discard_db_with_failures=False)
    databases_to_check = [databases[key]["database"] for key in databases]
    iterations = compare_baseline_with_iterations(baseline=baseline, databases_to_check=databases_to_check,
                                                  dataset_packages=package_names,
                                                  output_dir=output_dir, copy_to_output=True)

    save_comparison_iterations(app_info_db=app_info_db, output_dir=output_dir, iterations=iterations,
                               expected_packages=package_names, databases=databases_to_check)

    created_database = os.path.join(output_dir, "main.db")
    if os.path.exists(created_database):
        for db_to_check in databases_to_check:
            input_dir = Path(db_to_check).parent
            copy_faulty_to_output_dir(created_database, input_dir, os.path.join(output_dir, "faulty-apps"))
            copy_healthy_incompatible_to_output_dir(created_database, input_dir,
                                                    os.path.join(output_dir, "healthy-incompatible"))
            copy_healthy_compatible_to_output_dir(created_database, input_dir,
                                                  os.path.join(output_dir, "healthy-compatible"))


def compare_g4_acvtool_updated():
    output_dir = "I:\\\InstruMate\\g4_variant_comparisons_acvtool_updated\\"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    else:
        fs_utils.destroy_dir_files(output_dir)
        os.makedirs(output_dir)
    baseline_db = "H:\\InstruMate\\InstrumateAnalysis\\baseline\\main.db"
    app_info_db = "I:\\InstruMate\\acvtool-updated\\instrumate_log.db"
    query_packages = f"select distinct(package_name) from hc_iteration_views"
    package_names = [item[0] for item in execute_query(baseline_db, query_packages)]
    baseline = load_health_check_from_baseline_db(baseline_db=baseline_db, package_names=package_names,
                                                  iteration_number=199)
    tags = [['dataset-hc-g4-acvtool-updated', 0, 3]]
    databases, success_apps, failed_databases = find_databases_with_tags(tags,
                                                                         "I:\\InstruMate\\acvtool-updated\\hc-g4-acvtool-updated",
                                                                         forced_apps_exclusion=[],
                                                                         discard_db_with_failures=False)
    databases_to_check = [databases[key]["database"] for key in databases]
    iterations = compare_baseline_with_iterations(baseline=baseline, databases_to_check=databases_to_check,
                                                  dataset_packages=package_names,
                                                  output_dir=output_dir, copy_to_output=True)

    save_comparison_iterations(app_info_db=app_info_db, output_dir=output_dir, iterations=iterations,
                               expected_packages=package_names, databases=databases_to_check)

    created_database = os.path.join(output_dir, "main.db")
    if os.path.exists(created_database):
        for db_to_check in databases_to_check:
            input_dir = Path(db_to_check).parent
            copy_faulty_to_output_dir(created_database, input_dir, os.path.join(output_dir, "faulty-apps"))
            copy_healthy_incompatible_to_output_dir(created_database, input_dir,
                                                    os.path.join(output_dir, "healthy-incompatible"))
            copy_healthy_compatible_to_output_dir(created_database, input_dir,
                                                  os.path.join(output_dir, "healthy-compatible"))

def compare_g4_aspectj_apktool():
    output_dir = "I:\\InstruMate\\g4_variant_comparisons_aspectj_apktool\\"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    else:
        fs_utils.destroy_dir_files(output_dir)
        os.makedirs(output_dir)
    baseline_db = "H:\\InstruMate\\InstrumateAnalysis\\baseline\\main.db"
    app_info_db = "I:\\InstruMate\\aspectj-apktool\\instrumate_log.db"
    query_packages = f"select distinct(package_name) from hc_iteration_views"
    package_names = [item[0] for item in execute_query(baseline_db, query_packages)]
    baseline = load_health_check_from_baseline_db(baseline_db=baseline_db, package_names=package_names,
                                                  iteration_number=199)
    tags = [['dataset-hc-g4-aspectj-apktool', 0, 3]]
    databases, success_apps, failed_databases = find_databases_with_tags(tags,
                                                                         "I:\\InstruMate\\aspectj-apktool\\hc-aspectj-apktool",
                                                                         forced_apps_exclusion=[],
                                                                         discard_db_with_failures=False)
    databases_to_check = [databases[key]["database"] for key in databases]
    iterations = compare_baseline_with_iterations(baseline=baseline, databases_to_check=databases_to_check,
                                                  dataset_packages=package_names,
                                                  output_dir=output_dir, copy_to_output=True)

    save_comparison_iterations(app_info_db=app_info_db, output_dir=output_dir, iterations=iterations,
                               expected_packages=package_names, databases=databases_to_check)

    created_database = os.path.join(output_dir, "main.db")
    if os.path.exists(created_database):
        for db_to_check in databases_to_check:
            input_dir = Path(db_to_check).parent
            copy_faulty_to_output_dir(created_database, input_dir, os.path.join(output_dir, "faulty-apps"))
            copy_healthy_incompatible_to_output_dir(created_database, input_dir,
                                                    os.path.join(output_dir, "healthy-incompatible"))
            copy_healthy_compatible_to_output_dir(created_database, input_dir,
                                                  os.path.join(output_dir, "healthy-compatible"))


def compare_g4_aspectj_apkeditor():
    output_dir = "I:\\InstruMate\\g4_variant_comparisons_aspectj_apkeditor\\"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    else:
        fs_utils.destroy_dir_files(output_dir)
        os.makedirs(output_dir)
    baseline_db = "H:\\InstruMate\\InstrumateAnalysis\\baseline\\main.db"
    app_info_db = "I:\\InstruMate\\aspectj-apkeditor\\instrumate_log.db"
    query_packages = f"select distinct(package_name) from hc_iteration_views"
    package_names = [item[0] for item in execute_query(baseline_db, query_packages)]
    baseline = load_health_check_from_baseline_db(baseline_db=baseline_db, package_names=package_names,
                                                  iteration_number=199)
    tags = [['dataset-hc-g4-aspectj-apkeditor', 0, 3]]
    databases, success_apps, failed_databases = find_databases_with_tags(tags,
                                                                         "I:\\InstruMate\\aspectj-apkeditor\\hc-aspectj-apkeditor\\",
                                                                         forced_apps_exclusion=[],
                                                                         discard_db_with_failures=False)
    databases_to_check = [databases[key]["database"] for key in databases]
    iterations = compare_baseline_with_iterations(baseline=baseline, databases_to_check=databases_to_check,
                                                  dataset_packages=package_names,
                                                  output_dir=output_dir, copy_to_output=True)

    save_comparison_iterations(app_info_db=app_info_db, output_dir=output_dir, iterations=iterations,
                               expected_packages=package_names, databases=databases_to_check)

    created_database = os.path.join(output_dir, "main.db")
    if os.path.exists(created_database):
        for db_to_check in databases_to_check:
            input_dir = Path(db_to_check).parent
            copy_faulty_to_output_dir(created_database, input_dir, os.path.join(output_dir, "faulty-apps"))
            copy_healthy_incompatible_to_output_dir(created_database, input_dir,
                                                    os.path.join(output_dir, "healthy-incompatible"))
            copy_healthy_compatible_to_output_dir(created_database, input_dir,
                                                  os.path.join(output_dir, "healthy-compatible"))



def compare_g4_frida():
    output_dir = "I:\\InstruMate\\g4_variant_comparisons_frida\\"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    else:
        fs_utils.destroy_dir_files(output_dir)
        os.makedirs(output_dir)
    baseline_db = "H:\\InstruMate\\InstrumateAnalysis\\baseline\\main.db"
    app_info_db = "I:\\InstruMate\\g4_frida\\instrumate_log.db"
    query_packages = f"select distinct(package_name) from hc_iteration_views"
    package_names = [item[0] for item in execute_query(baseline_db, query_packages)]
    baseline = load_health_check_from_baseline_db(baseline_db=baseline_db, package_names=package_names,
                                                  iteration_number=199)
    tags = [['dataset-hc-frida', 0, 3]]
    databases, success_apps, failed_databases = find_databases_with_tags(tags,
                                                                         "I:\\InstruMate\\g4_frida\\hc-frida",
                                                                         forced_apps_exclusion=[],
                                                                         discard_db_with_failures=False)
    databases_to_check = [databases[key]["database"] for key in databases]
    iterations = compare_baseline_with_iterations(baseline=baseline, databases_to_check=databases_to_check,
                                                  dataset_packages=package_names,
                                                  output_dir=output_dir, copy_to_output=True)

    save_comparison_iterations(app_info_db=app_info_db, output_dir=output_dir, iterations=iterations,
                               expected_packages=package_names, databases=databases_to_check)

    created_database = os.path.join(output_dir, "main.db")
    if os.path.exists(created_database):
        for db_to_check in databases_to_check:
            input_dir = Path(db_to_check).parent
            copy_faulty_to_output_dir(created_database, input_dir, os.path.join(output_dir, "faulty-apps"))
            copy_healthy_incompatible_to_output_dir(created_database, input_dir,
                                                    os.path.join(output_dir, "healthy-incompatible"))
            copy_healthy_compatible_to_output_dir(created_database, input_dir,
                                                  os.path.join(output_dir, "healthy-compatible"))

def main():
    compare_g1_again()

if __name__ == "__main__":
    main()
