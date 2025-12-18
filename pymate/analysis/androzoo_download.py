import requests
import os
import time
from pymate.analysis.sqlite_helper import execute_query
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import os

def calculate_sha256(file_path):
    hash_sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as file:
            for chunk in iter(lambda: file.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception as e:
        print(f"Error reading file: {e}")
        return None

def is_file_valid(file_path):
    if not os.path.isfile(file_path):
        print(f"File does not exist: {file_path}")
        return False
    if os.path.getsize(file_path) == 0:
        print(f"File is empty: {file_path}")
        return False
    return True

def file_hash_matches_expected(file_path, expected_sha256):
    if not is_file_valid(file_path):
        return False, None
    calculated_hash = calculate_sha256(file_path)
    if calculated_hash is None:
        return False, None
    if calculated_hash.lower() == expected_sha256.lower():
        return True, calculated_hash.upper()
    return False, calculated_hash.upper()

def download_file(api_key, sha256, output_file):
    url = "https://androzoo.uni.lu/api/download"
    params = {
        "apikey": api_key,
        "sha256": sha256
    }
    max_retries = 10
    retry_delay = 10
    retry_max_time = 240  # seconds
    start_time = time.time()
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, stream=True)
            if response.status_code == 200:
                with open(output_file, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)
                return f"File downloaded successfully to {output_file}"
            else:
                print(f"Failed attempt {attempt+1}: HTTP {response.status_code}")
        except requests.RequestException as e:
            return f"Request failed (attempt {attempt+1}): {e}"
        if time.time() - start_time > retry_max_time:
            return "Retry max time reached, aborting."
        time.sleep(retry_delay)
    return "Download failed after maximum retries."


def download_androzoo_packages(database, output_dir):
    query = "SELECT sha256, pkg_name from tb_156_on_androzoo"
    items = execute_query(database, query)
    key = "0a34ff6b56a67972ad9f8bc60664287f689e50575f036d6bb637ce98b28ce9a7"
    futures = []
    qtd_removed_files = 0
    invalid_hash_files = [["pkg_name", "expected_sha256", "calculated_sha256"]]
    with ThreadPoolExecutor(max_workers=len(items)) as executor:
        for item in items:
            sha256 = item[0]
            pkg_name = item[1]
            file_name = os.path.join(output_dir, f"{pkg_name}.apk")
            if os.path.exists(file_name):
                valid_hash, calculated_hash = file_hash_matches_expected(file_name, sha256)
                if not valid_hash:
                    print(f"removing file {file_name} - incomplete")
                    os.remove(file_name)
                    qtd_removed_files = qtd_removed_files + 1
                    invalid_hash_files.append([pkg_name, sha256, calculated_hash])
            if not os.path.exists(file_name):
                print(f"downloading file {file_name}")
                future = executor.submit(download_file, api_key=key, sha256=sha256, output_file=file_name)
                futures.append(future)
            else:
                print(f"file already downloaded {pkg_name}")
    for future in as_completed(futures):
        print(future.result())
    print(f"Removed files because of wrong hash: {qtd_removed_files}")
    print(f"Len problematic files {len(invalid_hash_files)}")
    for item in invalid_hash_files:
        print(";".join(item))

if __name__ == "__main__":
    output_dir = "D:\\Androzoo\\156-androzoo\\"
    database = "D:\\Androzoo\\androzoo-05-03-2025.db"
    download_androzoo_packages(database,output_dir)