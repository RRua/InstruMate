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


def plot_line_chart_old(data, base_folder=None, file_name=None, title="Observation Count", no_label=True):
    structured_data = {}
    for package, iteration, count in data:
        if package not in structured_data:
            structured_data[package] = {}
        structured_data[package][iteration] = count
    iterations = sorted({item[1] for item in data})
    plt.figure(figsize=(10, 6))
    for package, observations in structured_data.items():
        y_values = [observations.get(iteration, 0) for iteration in iterations]
        plt.plot(iterations, y_values, marker="o", label=None if no_label else package)

    # Customizing the plot
    plt.title(f"{title} Per Iteration for Packages")
    plt.xlabel("Iteration Number")
    plt.ylabel("Observation Count")
    plt.legend(title="Packages")
    plt.grid(True)
    # Ensure the base folder exists
    os.makedirs(base_folder, exist_ok=True)

    if base_folder is not None and file_name is not None:
        file_path = os.path.join(base_folder, file_name)
        plt.savefig(file_path)
    plt.show()


def per_package_plots(packages, saved_db, base_logs_dir, qualifier, show=False):
    if packages is not None and len(packages) > 0:
        tmp = "','".join(packages)
        sub_packages_query = f"where package_name in ('{tmp}')"
    else:
        sub_packages_query = ""
    score_views_tmp = execute_query(saved_db,
                                    f"select package_name, iteration, score from hc_iteration_views {sub_packages_query} order by package_name asc, CAST(iteration AS INTEGER) asc")
    summary_view_scores = [[item[0], int(item[1]), float(item[2])] for item in score_views_tmp]
    plot_line_chart(summary_view_scores, base_folder=base_logs_dir, file_name=f"summary_view_scores_{qualifier}.png",
                    title=f"View Items {qualifier}")

    summary_exception_scores_tmp = execute_query(saved_db,
                                                 f"select package_name, iteration, score from hc_iteration_exceptions {sub_packages_query} order by package_name asc, CAST(iteration AS INTEGER) asc")
    summary_exception_scores = [[item[0], int(item[1]), float(item[2])] for item in summary_exception_scores_tmp]
    plot_line_chart(summary_exception_scores, base_folder=base_logs_dir,
                    file_name=f"summary_exception_scores_{qualifier}.png",
                    title=f"Exceptions Items {qualifier}")

    summary_exception_sites_scores_tmp = execute_query(saved_db,
                                                       f"select package_name, iteration, score from hc_iteration_exception_sites {sub_packages_query} order by package_name asc, CAST(iteration AS INTEGER) asc")
    summary_exception_sites_scores = [[item[0], int(item[1]), float(item[2])] for item in
                                      summary_exception_sites_scores_tmp]
    plot_line_chart(summary_exception_sites_scores, base_folder=base_logs_dir,
                    file_name=f"summary_exception_sites_scores_{qualifier}.png",
                    title=f"Exception Sites {qualifier}")

    score_evolution_tmp = execute_query(saved_db,
                                        f"select score_category, iteration, sum(qtd_scored_apps) from vw_score_evolution {sub_packages_query} group by score_category, iteration order by score_category asc, CAST(iteration AS INTEGER) asc")
    score_evolution = [[item[0], int(item[1]), int(item[2])] for item in score_evolution_tmp]
    plot_line_chart(score_evolution, base_folder=base_logs_dir,
                    file_name=f"score_evolution_{qualifier}.png", title=f"Score Evolution  {qualifier}", show=show)


def global_plots(saved_db, base_logs_dir, size, show=False):
    new_views_per_iteration_tmp = execute_query(saved_db,
                                                f"select * from vw_saturation_new_items ")
    new_views_per_iteration = [[item[0], int(item[1]), int(item[2])] for item in new_views_per_iteration_tmp]
    plot_line_chart(new_views_per_iteration, base_folder=base_logs_dir,
                    file_name=f"vw_saturation_new_items.png", title=f"vw_saturation_new_items", show=show)

    new_views_per_iteration_avg = [[item[0], int(item[1]), int(item[2]) * 1.0 / size] for item in
                                   new_views_per_iteration_tmp]
    plot_line_chart(new_views_per_iteration_avg, base_folder=base_logs_dir,
                    file_name=f"vw_saturation_new_items_avg.png", title=f"vw_saturation_new_items_avg", show=show)

    new_views_per_iteration_tmp = execute_query(saved_db,
                                                f"select * from vw_saturation_scored_apps ")
    new_views_per_iteration = [[item[0], int(item[1]), int(item[2])] for item in new_views_per_iteration_tmp]
    plot_line_chart(new_views_per_iteration, base_folder=base_logs_dir,
                    file_name=f"vw_saturation_scored_apps.png", title=f"vw_saturation_scored_apps", show=show)

def final_plots():
    base_logs_dir = "H:\\InstruMate\\InstrumateAnalysis\\baseline\\"
    saved_db = os.path.join(base_logs_dir, "main.db")
    vw_stacked_bar_exception_sites_iterations = execute_query(saved_db, "select iteration, total_prev_pct, total_new_pct from vw_stacked_bar_exception_sites_iterations")
    plot_stacked_bar_chart(vw_stacked_bar_exception_sites_iterations, "Exception-Sites", base_logs_dir, "vw_stacked_bar_exception_sites_iterations.png")


def after_plots_old():
    base_logs_dir = "H:\\InstruMate\\InstrumateAnalysis\\baseline\\"
    saved_db = os.path.join(base_logs_dir, "main.db")
    query_packages = "select DISTINCT(package_name) from hc_iteration_views order by package_name"
    packages = [item[0] for item in execute_query(saved_db, query_packages)]
    per_package_plots(packages, saved_db, base_logs_dir, "all")

    size = len(packages)
    m = 20
    parts = size // m
    for i in range(parts):
        parts_array = packages[i * m: i * m + m - 1]
        per_package_plots(parts_array, saved_db, base_logs_dir, f"split{i}")
    global_plots(saved_db, base_logs_dir, size)

def plot_line_chart(data, base_folder=None, file_name=None, title="Observation Count", no_label=False, show=False):
    monitor = get_monitors()[0]  # Use the first monitor
    screen_width = monitor.width
    screen_height = monitor.height

    # Configure the figure size to match the monitor's resolution
    dpi = 100  # Dots per inch
    figsize = (screen_width / dpi, screen_height / dpi)  # Size in inches

    structured_data = {}
    for package, iteration, count in data:
        if package not in structured_data:
            structured_data[package] = {}
        structured_data[package][iteration] = count

    iterations = sorted({item[1] for item in data})
    plt.figure(figsize=figsize, dpi=dpi)
    for package, observations in structured_data.items():
        y_values = [observations.get(iteration, 0) for iteration in iterations]
        plt.plot(iterations, y_values, marker="o", label=None if no_label else package)

    # Customizing the plot
    plt.title(f"{title} Per Iteration for Packages")
    plt.xlabel("Iteration Number")
    plt.ylabel("Observation Count")

    # Add legend to the left of the plot without overlapping the chart
    if not no_label:
        plt.legend(title="Packages", loc='center left', bbox_to_anchor=(-0.15, 0.5))

    plt.grid(True)

    # Ensure the base folder exists
    if base_folder is not None:
        os.makedirs(base_folder, exist_ok=True)
        if file_name is not None:
            file_path = os.path.join(base_folder, file_name)
            plt.savefig(file_path)
            print(f"Plot saved to {file_path}")

    if show:
        plt.show()


def plot_stacked_bar_chart(data, observed_label, base_folder, img_file_name, show=False):
    # Convert data to numpy array for easier manipulation
    data = np.array(data)

    # Extract values
    experiment_numbers = data[:, 0]  # Experiment numbers (can be floats or ints)
    seen_before = data[:, 1].astype(float)  # Elements seen before
    new_elements = data[:, 2].astype(float)  # New elements not seen before

    # Plot stacked bar chart
    plt.figure(figsize=(10, 6))
    plt.bar(experiment_numbers, seen_before, label="Seen Before", color='steelblue', width=0.8)
    plt.bar(experiment_numbers, new_elements, bottom=seen_before, label="New Elements", color='orange', width=0.8)

    # Add labels and title
    plt.xlabel("Experiment Number")
    plt.ylabel("Number of Elements")
    plt.title(f"Evolution of Observed {observed_label} per Experiment")
    plt.legend()
    plt.xticks(ticks=experiment_numbers, labels=[f"{x:.2f}" for x in experiment_numbers], rotation=45)
    plt.tight_layout()
    # Ensure the base folder exists
    if base_folder is not None:
        os.makedirs(base_folder, exist_ok=True)
        if img_file_name is not None:
            file_path = os.path.join(base_folder, img_file_name)
            plt.savefig(file_path)
            print(f"Plot saved to {file_path}")
    if show:
        plt.show()