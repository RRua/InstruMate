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


def query_table_data(database, add_originals=True):
    columns = ["maker_tag", "multimedia", "java",
               "presentation",
               "configuration",
               "rich_documents",
               "compressed_files",
               "crypto_files",
               "javascript",
               "automation",
               "source_code",
               "compiled_dex",
               "compiled_native",
               "binary",
               "text_files",
               "unknown_files"]
    columns_str = ", ".join(columns)
    if add_originals:
        query_originals = f"""
        select {columns_str} from vw_final_originals_content_type_analysis
        union all
        """
    else:
        query_originals = ""
    query = f"""
    {query_originals}
    select {columns_str} from vw_final_content_type_analysis 
    union all 
    select {columns_str} from vw_final_content_type_analysis_merged_apps"""
    res = execute_query(db_path=database, query=query)
    res.insert(0, columns)
    transposed = [[row[i] for row in res] for i in range(len(res[0]))]
    return transposed


def calc_pct(original_count, computed_value):
    original_count = int(original_count)
    if original_count == 0:
        return 0
    computed_value = int(computed_value)
    pct = ((original_count - computed_value) * 100) / original_count
    return str(round(pct)) + "\\%"


def save_content_type_table(table_data, filename, add_originals=False):
    rows = []
    removed_rows = ["java", "javascript", "crypto_files"]
    renamed_rows = {"unknown_files": "other_files",
                    "source_code": "interpreted_code"}
    col_count = -1
    for i, item in enumerate(table_data):
        oc = item[1] if i > 0 else 0
        if item[0] in removed_rows:
            continue
        content_type_str = item[0]
        if content_type_str in renamed_rows:
            content_type_str = renamed_rows[content_type_str]
        content_type_str = content_type_str.replace('_', ' ').capitalize()
        if i > 0:
            row = []
            if col_count == -1:
                col_count = len(item)
            for c, citem in enumerate(item):
                if c == 0:
                    row.append(content_type_str)
                else:
                    if c == 1 and not add_originals:
                        continue
                    else:
                        row.append(str(citem))
                        row.append(calc_pct(oc, citem))
            row_str = " & ".join(row)
            rows.append(f"{row_str} \\\\ \\hline  ")
    rws_str = "\n".join(rows)
    cols_spec = "c|" * ((col_count - 1) * 2 + 1)
    if add_originals:
        headers = ["Category", "Original", "Mz", "Me", "Ma", "MeM"]
    else:
        headers = ["Category", "Mz", "Me", "Ma", "MeM"]
    headers_str = ["\\multicolumn{2}{|c|}{\\textbf{" + item + "}}" for i, item in enumerate(headers) if i > 0]
    headers_str.insert(0, headers[0])
    latex_str = """
\\begin{table}[h]
    \\centering
    \\small
    \\renewcommand{\\arraystretch}{1.2} % Adjust row height
    \\setlength{\\tabcolsep}{1.4pt}       % Adjust column spacing
    \\caption{Summary of health check results by variant maker}
    \\label{table:content_type_analysis}
    \\begin{tabular}{|""" + cols_spec + """} \\hline
        """ + (" & ".join(headers_str)) + """ \\\\ \\hline
        """ + rws_str + """
    \\end{tabular}
\\end{table}"""
    with open(filename, "w") as f:
        f.write(latex_str)


def main():
    database = "I:\\InstruMate\\g1-content-type\\instrumate_log.db"
    table_data = query_table_data(database)
    save_content_type_table(table_data, "I:\\InstruMate\\g1-content-type\\latex_table.txt")


if __name__ == "__main__":
    main()
