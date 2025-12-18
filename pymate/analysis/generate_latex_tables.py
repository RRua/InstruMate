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


def query_type(database, package_name):
    query_type_i = f"""select * from vw_health_incompatible_apps where package_name='{package_name}'"""
    query_type_f = f"""select * from vw_faulty_apps where package_name='{package_name}'"""
    res_i = execute_query(db_path=database, query=query_type_i)
    res_f = execute_query(db_path=database, query=query_type_f)
    if len(res_i) > 0:
        return "I"
    if len(res_f) > 0:
        return "F"
    return "U"


def string_to_set(s):
    return ast.literal_eval(s) if s != "set()" else set()


def parse_set_of_sets(s):
    set_out = set()
    for item in s.split(';'):
        temp = string_to_set(item)
        for i_item in temp:
            if isinstance(i_item, tuple):
                set_out.add(i_item)
            elif isinstance(i_item, set):
                set_out.update(i_item)
            else:
                raise RuntimeError(f"{i_item} is neither a tuple nor a set.")
    return set_out


def save_latex_table_without_type(filename, data, label, group_tag, ui_packages=None, esites_packages=None):
    txt_ui_elements = """Rows marked with an asterisk (*) denote apps that include UI elements not seen before. """
    txt_esites = """Rows marked with a double asterisk (**) denote apps that include components traced to protection mechanisms with the insights obtained from exception sites."""
    if ui_packages is None or len(ui_packages) == 0:
        txt_ui_elements = ""
        ui_packages = []
    if esites_packages is None or len(esites_packages) == 0:
        txt_esites = ""
        esites_packages = []
    with open(filename, "w") as f:
        thead = """\\centering
                \\small
                \\begin{longtable}{|p{0.02\\textwidth}|p{0.28\\textwidth}|p{0.60\\textwidth}|}
                \\hline
                 & ID & Exception-sites \\\\ \hline
                \\endhead"""
        f.write(thead)

        f.write("\n")
        pos = 1
        for item in data:
            package_name = item[0].strip()
            package_name_str = package_name
            if package_name in ui_packages:
                package_name_str = package_name_str + "*"
                if package_name in esites_packages:
                    package_name_str = package_name_str + " **"
            else:
                if package_name in esites_packages:
                    package_name_str = package_name_str + "**"
            package_name_str = package_name_str.replace("_", r"\_")

            exception_sites_set = item[2]
            exception_sites_set_str = "{}"
            if len(exception_sites_set) > 0:
                exception_sites_set_str = str(exception_sites_set)
            exception_sites_set_str = exception_sites_set_str.replace("_", r"\_").replace("}", "\\}").replace("{", "\\{")

            tbody = "\t\\makecell[tl]{" + str(pos) + "} &	\\makecell[tl]{" + package_name_str + "} &	\\makecell[tl]{" + exception_sites_set_str + "} \\\\ \\hline"""
            f.write(tbody)
            f.write("\n")
            f.write("\n")
            pos += 1
        tending = """\\caption{Resilient and divergent apps with their exception sites found during the health check procedures with variants in """ + group_tag + """. """+txt_ui_elements+txt_esites+""" }
\\label{table:""" + label + """}
\\end{longtable}"""
        f.write(tending)
        f.write("\n")


def generate_latex_table(databases, exceptions_file, label, group_tag, corrected_packages=None, ui_packages=None, esites_packages=None, external_selected_apps=None):
    if corrected_packages is None:
        corrected_packages = []
    corrected_packages_str = ",".join([f"'{p}'" for p in corrected_packages])
    if external_selected_apps is None or len(external_selected_apps) == 0:
        query_exception_sites = """select package_name,group_concat(catenated_exception_sites) as catenated_exception_sites
        from (
        select package_name, app_id, catenated_exception_sites, "F" as classification from vw_variants_with_catenated_ui_and_esites
        where package_name in (select package_name from vw_faulty_apps)
        union ALL
        select package_name,  app_id, catenated_exception_sites, "I" as classification from vw_variants_with_catenated_ui_and_esites
        where package_name in (select package_name from vw_health_incompatible_apps)
        union ALL
        select package_name,  app_id, catenated_exception_sites, "I" as classification from vw_variants_with_catenated_ui_and_esites
        where package_name in (""" + corrected_packages_str + """)
        )group by package_name order by package_name"""
    else:
        external_selected_apps_str = ",".join([f"'{p}'" for p in external_selected_apps])
        query_exception_sites = """select package_name,group_concat(catenated_exception_sites) as catenated_exception_sites
                from (
                select package_name, app_id, catenated_exception_sites, "F" as classification from vw_variants_with_catenated_ui_and_esites
                where package_name in (select package_name from vw_faulty_apps)
                union ALL
                select package_name,  app_id, catenated_exception_sites, "I" as classification from vw_variants_with_catenated_ui_and_esites
                where package_name in (select package_name from vw_health_incompatible_apps)
                union ALL
                select package_name,  app_id, catenated_exception_sites, "I" as classification from vw_variants_with_catenated_ui_and_esites
                where package_name in (""" + corrected_packages_str + """)
                )
                where package_name in (""" + external_selected_apps_str + """)
                or package_name in (""" + corrected_packages_str + """)
                group by package_name order by package_name"""

    collected_packages = {}
    for db in databases:
        exception_sites = execute_query(db_path=db, query=query_exception_sites)
        for es in exception_sites:
            package_name = es[0]
            catenated_exception_sites = parse_set_of_sets(es[1])
            package_status = query_type(db, package_name)
            if package_name not in collected_packages:
                collected_packages[package_name] = {
                    "package_name": package_name,
                    "package_status": package_status,
                    "exception_sites": catenated_exception_sites
                }
            else:
                collected_packages[package_name]["exception_sites"].update(catenated_exception_sites)
    table_data = []
    for key in collected_packages:
        package_name = key
        package_status = collected_packages[key]["package_status"]
        exception_sites = collected_packages[key]["exception_sites"]
        table_data.append([package_name, package_status, exception_sites])
        print(f"{package_name}: {package_status}: {exception_sites}")
    save_latex_table_without_type(exceptions_file, table_data, label, group_tag, ui_packages, esites_packages)


def main():
    androlog_db = "H:\\InstruMate\\InstrumateAnalysis\\g4_variant_comparisons_androlog_v3\\main.db"
    acvtool_db = "H:\\InstruMate\\InstrumateAnalysis\\g4_variant_comparisons_acvtool\\main.db"
    aspectj_e_db = "I:\\InstruMate\\g4_variant_comparisons_aspectj_apkeditor\\main.db"
    aspectj_a_db = "I:\\InstruMate\\g4_variant_comparisons_aspectj_apktool\\main.db"
    frida_db = "I:\\InstruMate\\g4_variant_comparisons_frida\\main.db"
    output_dir = "I:\\InstruMate\\latex_tables"
    generate_latex_table(databases=["H:\\InstruMate\\InstrumateAnalysis\\g1_variant_comparisons_v3\\main.db"],
                         exceptions_file=os.path.join(output_dir, "g1_exceptions.tex"), label="g1_group",
                         group_tag="G1 group", corrected_packages=["com.intsig.camscanner"],
                         ui_packages=["com.intsig.camscanner", "com.microsoft.office.officehubrow", "com.microsoft.office.onenote"],
                         esites_packages=["com.microsoft.office.excel", "com.microsoft.office.officehubrow", "com.microsoft.office.onenote",
                                          "com.microsoft.office.powerpoint", "com.microsoft.office.word",
                                          "com.miniclip.carrom", "com.roblox.client", "com.vectorunit.purple.googleplay", "com.hp.android.printservice"])

    generate_latex_table(databases=["H:\\InstruMate\\InstrumateAnalysis\\g2_variant_comparisons_v3_leo\\main.db"],
                         exceptions_file=os.path.join(output_dir, "g2_exceptions.tex"), label="g2_group",
                         group_tag="G2 group")

    generate_latex_table(databases=["H:\\InstruMate\\InstrumateAnalysis\\g3_variant_comparisons_v1\\main.db"],
                         exceptions_file=os.path.join(output_dir, "g3_exceptions.tex"), label="g3_group",
                         group_tag="G3 group")

    generate_latex_table(databases=[androlog_db],
                         exceptions_file=os.path.join(output_dir, "g4_exceptions_androlog.tex"),
                         label="g4_group_androlog", group_tag="G4 group instrumented by Androlog")

    generate_latex_table(databases=[acvtool_db],
                         exceptions_file=os.path.join(output_dir, "g4_exceptions_acvtool.tex"),
                         label="g4_group_acvtool", group_tag="G4 group instrumented by ACVTool")

    generate_latex_table(
        databases=[aspectj_e_db],
        exceptions_file=os.path.join(output_dir, "g4_exceptions_aspectj_apkeditor.tex"), label="g4_group_aspectj_e",
        group_tag="G4 group instrumented by AspectJ with ApkTool")

    generate_latex_table(
        databases=[aspectj_a_db],
        exceptions_file=os.path.join(output_dir, "g4_exceptions_aspectj_apktool.tex"), label="g4_group_aspectj_a",
        group_tag="G4 group instrumented by AspectJ with ApkEditor")

    generate_latex_table(
        databases=[aspectj_e_db, aspectj_a_db],
        exceptions_file=os.path.join(output_dir, "g4_exceptions_aspectj_apkeditor_plus_apktool.tex"),
        label="g4_group_aspectj", group_tag="G4 group instrumented with AspectJ")

    generate_latex_table(
        databases=[frida_db],
        exceptions_file=os.path.join(output_dir, "g4_frida.tex"), label="g4_group_frida",
        group_tag="G4 group instrumented with Frida")


    query_g4_external = """select DISTINCT package_name from (
select package_name from vw_faulty_apps
union all 
select package_name from vw_healthy_incompatible_apps)"""
    external_db = "I:\\InstruMate\\g4_consolidated_v2\\consolidated.db"
    packages = [item[0] for item in execute_query(db_path=external_db, query=query_g4_external)]
    generate_latex_table(
        databases=[androlog_db, acvtool_db, aspectj_e_db, aspectj_a_db, frida_db],
        exceptions_file=os.path.join(output_dir, "g4_all.tex"), label="g4_group_all",
        group_tag="G4 group", external_selected_apps=packages,
        ui_packages=["com.billiards.city.pool.nation.club", "com.jio.myjio", "com.firsttouchgames.story",
                     "com.cyberlink.youcammakeup"],
        esites_packages=["com.firsttouchgames.story", "com.jio.myjio", "com.myntra.android", "com.utorrent.client", "com.vkontakte.android"],
        corrected_packages=["com.billiards.city.pool.nation.club", "com.jio.myjio", "com.firsttouchgames.story",
                     "com.cyberlink.youcammakeup"]
    )


if __name__ == "__main__":
    main()
