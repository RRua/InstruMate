
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
from pymate.analysis.baseline import create_baseline_from_iterations
import subprocess
import matplotlib.pyplot as plt
import numpy as np
import os
from xml.etree import ElementTree as ET


def combine_svgs_side_by_side(svg_file1, svg_file2, output_file):
    tree1 = ET.parse(svg_file1)
    root1 = tree1.getroot()
    tree2 = ET.parse(svg_file2)
    root2 = tree2.getroot()
    width1 = float(root1.attrib.get("width", "0").replace("px", "").replace("pt", ""))
    height1 = float(root1.attrib.get("height", "0").replace("px", "").replace("pt", ""))
    width2 = float(root2.attrib.get("width", "0").replace("px", "").replace("pt", ""))
    height2 = float(root2.attrib.get("height", "0").replace("px", "").replace("pt", ""))

    combined_width = width1 + width2
    combined_height = max(height1, height2)

    svg_ns = "http://www.w3.org/2000/svg"
    ET.register_namespace("", svg_ns)
    new_root = ET.Element("svg", attrib={
        "xmlns": svg_ns,
        "width": f"{combined_width}px",
        "height": f"{combined_height}px",
        "viewBox": f"0 0 {combined_width} {combined_height}"
    })
    new_root.append(root1)

    transform_group = ET.Element("g", attrib={"transform": f"translate({width1}, 0)"})
    transform_group.append(root2)
    new_root.append(transform_group)

    ET.ElementTree(new_root).write(output_file)
    print(f"Combined SVG saved to {output_file}")


def convert_svg_to_emf(inkscape_exe = "C:\\Program Files\\Inkscape\\bin\\inkscape.exe", svg_file=None, emf_file=None ):
    subprocess.run([inkscape_exe, svg_file, '--export-filename', emf_file])

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
    plt.title(f"{title}")
    plt.xlabel("Iteration Number")
    plt.ylabel("Observation Count")

    # Add legend to the left of the plot without overlapping the chart
    if not no_label:
        plt.legend(title="", loc='center left', bbox_to_anchor=(0.5, 0.5))

    plt.grid(True)

    # Ensure the base folder exists
    if base_folder is not None:
        os.makedirs(base_folder, exist_ok=True)
        if file_name is not None:
            file_path_png = os.path.join(base_folder, f"{file_name}.png")
            file_path_svg = os.path.join(base_folder, f"{file_name}.svg")
            file_path_emf = os.path.join(base_folder, f"{file_name}.emf")
            plt.savefig(file_path_png)
            plt.savefig(file_path_svg, format='svg')
            # convert_svg_to_emf(svg_file=file_path_svg, emf_file=file_path_emf)
            print(f"Plot saved to {file_path_png} and {file_path_svg} and {file_path_emf}")

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

    # Configure X-axis ticks to show every 10 numbers
    min_x = int(min(experiment_numbers))
    max_x = int(max(experiment_numbers))
    tick_positions = np.arange(min_x, max_x + 1, 10)
    plt.xticks(ticks=tick_positions)

    # Add labels and title
    plt.xlabel("Experiment Number")
    plt.ylabel("Number of Elements")
    plt.title(f"Evolution of Observed {observed_label} per Experiment")
    plt.legend()
    plt.tight_layout()

    # Ensure the base folder exists and save the plot
    if base_folder is not None:
        os.makedirs(base_folder, exist_ok=True)
        if img_file_name is not None:
            file_path = os.path.join(base_folder, img_file_name)
            plt.savefig(file_path)
            print(f"Plot saved to {file_path}")

    # Show the plot if required
    if show:
        plt.show()
