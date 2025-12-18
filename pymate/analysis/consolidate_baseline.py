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
from pymate.analysis.baseline import HealthCheck, HealthCheckIteration
from pymate.analysis.sqlite_helper import execute_query
from pymate.analysis.baseline import create_baseline_from_iterations, find_databases_with_tags

def find_databases(input_dir, max_hc):
    # intermitent failiures
    forced_apps_exclusion = ['com.jrzheng.supervpnfree',
                             'eu.nordeus.topeleven.android',
                             'com.ea.gp.fifamobile',
                             'com.einnovation.temu',
                             'com.yandex.browser',
                             'com.outfit7.talkingtom2free',
                             'com.fungames.blockcraft',
                             'com.halo.wifikey.wifilocating',
                             'com.shopee.br',
                             'com.gamma.scan',
                             'com.FDGEntertainment.redball4.gp',
                             'com.rioo.runnersubway',
                             'com.microsoft.skydrive',
                             'homeworkout.homeworkouts.noequipment',
                             'com.playgendary.kickthebuddy',
                             "com.king.bubblewitch3",
                             "com.biglime.cookingmadness",
                             "com.rovio.baba",
                             "net.mobigame.zombietsunami",
                             "com.king.farmheroessaga",
                             "com.miniclip.agar.io",
                             "com.microsoft.office.outlook",
                             "com.taxsee.taxsee"
                             ]
    tags = [['baseline-hc', 0, max_hc]]
    databases, success_apps, failed_databases = find_databases_with_tags(tags, input_dir,
                                                                         forced_apps_exclusion=forced_apps_exclusion)
    print("Health checks selected: ")
    print([key for key in databases])
    print(f"Number of apps {len(success_apps)}")
    dataset_packages = [item for item in success_apps if item not in forced_apps_exclusion]
    databases_array = [databases[key]["database"] for key in databases][:200]
    return databases_array, dataset_packages, failed_databases


def main():
    output_dir = "H:\\InstruMate\\InstrumateAnalysis\\baseline\\"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    else:
        fs_utils.destroy_dir_files(output_dir)
        os.makedirs(output_dir)
    input_dir = "H:\\InstruMate\\InstrumateAnalysis\\baseline-hc\\"
    databases_to_check, dataset_packages, failed_databases = find_databases(input_dir, max_hc=200)
    print(f"Health apps {len(dataset_packages)}")
    print(f"Databases to check {len(databases_to_check)}")
    create_baseline_from_iterations(databases_to_check=databases_to_check, dataset_packages=dataset_packages,
                                    output_dir=output_dir, failed_databases=failed_databases, copy_to_output=True)


if __name__ == "__main__":
    main()
    # final_plots()
