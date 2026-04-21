import json
import os
import re
import csv
import shutil
import subprocess
import hashlib
import random
import string


def is_windows():
    return os.name == 'nt'


def get_number_from_filename(filename):
    match = re.search(r'(\d+)_', filename)
    if match:
        return int(match.group(1))
    return 1000


def compile_ts(contents):
    try:
        in_file = "./tmp/input.ts"
        out_file = "./tmp/output.js"
        temp1 = open(in_file, 'w')
        temp1.write(contents)
        temp1.close()
        print(f"Compiling TS contents from {in_file} to {out_file}")

        command = ["frida-compile", in_file, "-o", out_file]
        subprocess.run(command, check=True)
        temp2 = open(out_file, 'r', encoding='utf8', newline='\n')
        temp2.seek(0)
        contents_of_temp_file2 = temp2.read()
        return contents_of_temp_file2
        print("frida-compile completed successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error running frida-compile: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def join_scripts(file_dictionary, BLACKLIST, category):
    concatenated_contents = ""
    for file_path, file_position in file_dictionary.items():
        file_name = os.path.basename(file_path)
        if file_name not in BLACKLIST:
            print(f"Loading {category} Module {file_position} {file_path}")
            try:
                with open(file_path, "r") as file:
                    file_contents = file.read()
                    concatenated_contents += file_contents
                    concatenated_contents += "\n"
            except FileNotFoundError:
                print(f"File not found: {file_path}")
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
        else:
            print(f"Skiped Module {file_position} {file_path}")
    return concatenated_contents


def write_dict_as_json(json_dict, base_dir, file_name, overwrite_existing=False):
    json_str = json.dumps(json_dict, indent=4)
    file_path = os.path.join(base_dir, file_name)
    os.makedirs(base_dir, exist_ok=True)
    if not os.path.exists(file_path) or overwrite_existing:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(json_str)


def dict_as_formatted_json(json_dict: dict):
    json_str = json.dumps(json_dict, indent=4)
    return json_str


def read_json_as_dict(file_name, base_dir=None):
    file_path = file_name
    if base_dir is not None:
        file_path = os.path.join(base_dir, file_name)
    data = None
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    return data


def write_dict_array_as_csv(array, base_dir, file_name, overwrite_existing=False):
    header = set()
    for item in array:
        for key in item:
            header.add(key)
    rows = []
    rows.append(list(header))
    for item in array:
        row = []
        for key in header:
            row.append(item[key] if key in item else None)
        rows.append(row)
    write_array_as_csv(rows, base_dir, file_name, overwrite_existing)


def write_array_as_csv(array, base_dir, file_name, overwrite_existing=False):
    file_path = os.path.join(base_dir, file_name)
    os.makedirs(base_dir, exist_ok=True)
    if not os.path.exists(file_path) or overwrite_existing:
        with open(file_path, "w", newline='', encoding='utf-8') as fd:
            csv_writer = csv.writer(fd)
            for row in array:
                csv_writer.writerow(row)


def copy_file_if_not_exists(source, dest_file_name, dest_base_dir=None, overwrite_existing=False):
    if dest_base_dir is not None:
        file_path = os.path.join(dest_base_dir, dest_file_name)
    else:
        file_path = dest_file_name
    if not os.path.exists(file_path) or overwrite_existing:
        shutil.copy(source, file_path)

def is_primitive(var):
    return isinstance(var, (int, float, str, bool))


def is_list_or_set(var):
    return isinstance(var, (list, set))


def is_dictionary(var):
    return isinstance(var, dict)


def diff_list_or_set(list_a, list_b):
    assert isinstance(list_a, (list, set))
    assert isinstance(list_b, (list, set))
    filtered_list_a = [d for d in list_a if d is not None]
    filtered_list_b = [d for d in list_b if d is not None]
    removed_items = [d for d in filtered_list_a if d not in filtered_list_b]
    added_items = [d for d in filtered_list_b if d not in filtered_list_a]
    # kept_keys = [list(d.keys()) for d in filtered_list_a+filtered_list_b if d not in removed_items and d not in added_items]
    # kept_set = {item for sublist in kept_keys for item in sublist}
    return {
        "removed": list(removed_items),
        "added": list(added_items),
    }


def diff_dictionaries(dict_a, dict_b):
    assert isinstance(dict_a, dict)
    assert isinstance(dict_b, dict)
    dict_a_keys_set = set(dict_a.keys())
    dict_b_keys_set = set(dict_b.keys())
    removed = dict_a_keys_set - dict_b_keys_set
    added = dict_b_keys_set - dict_a_keys_set
    kept = dict_a_keys_set & dict_b_keys_set
    changed = {}
    for key in kept:
        value_in_a = dict_a[key]
        value_in_b = dict_b[key]
        if isinstance(value_in_a, dict) and isinstance(value_in_b, dict):
            change = diff_dictionaries(value_in_a, value_in_b)
        else:
            if isinstance(value_in_a, (list, set)) and isinstance(value_in_b, (list, set)):
                change = diff_list_or_set(value_in_a, value_in_b)
            else:
                change = {
                    "from": value_in_a,
                    "to": value_in_b
                }
        changed[key] = change
    return {
        "removed": list(removed),
        "added": list(added),
        "changed": list(changed)
    }


def diff_values(val1, val2):
    if is_primitive(val1) or is_primitive(val2):
        if val1 != val2:
            return {
                "from": val1,
                "to": val2
            }
        else:
            return {}
    if is_list_or_set(val1) and is_list_or_set(val2):
        return diff_list_or_set(val1, val2)
    if is_dictionary(val1) and is_dictionary(val2):
        return diff_dictionaries(val1, val2)
    raise RuntimeError(f"Cant compare {val1} {val2}")


def list_dir_files(directory_path, base_dir=None):
    res = []
    if base_dir is not None:
        file_path = os.path.join(base_dir, directory_path)
    else:
        file_path = directory_path
    for root, dirs, files in os.walk(file_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                res.append(file_path)
            except Exception as e:
                print(f"Error removing {file_path}: {e}")
    return res


def copy_dir_files(src_dir, dst_dir, src_base_dir=None, dst_base_dir=None):
    if src_base_dir is not None:
        src_path = os.path.join(src_base_dir, src_dir)
    else:
        src_path = src_dir
    if dst_base_dir is not None:
        dst_path = os.path.join(dst_base_dir, dst_dir)
    else:
        dst_path = dst_dir
    os.makedirs(dst_path, exist_ok=True)
    for root, dirs, files in os.walk(src_path):
        for file_name in files:
            src_file_path = os.path.join(root, file_name)
            if os.path.isfile(src_file_path):
                relative_path = os.path.relpath(root, src_path)
                tmp = os.path.join(dst_path, relative_path)
                if not os.path.exists(tmp):
                    os.makedirs(tmp)
                dest_file_path = os.path.join(tmp, file_name)
                if not os.path.exists(dest_file_path):
                    try:
                        shutil.copy(src_file_path, dest_file_path)
                    except Exception as e:
                        print(f"Error copying {src_file_path} to {dest_file_path}: {e}")
            if os.path.isdir(src_file_path):
                dest_file_path = os.path.join(dst_path, file_name)
                if not os.path.exists(dest_file_path):
                    os.makedirs(dest_file_path)


def get_md5_hash_for_str(str_to_hash:str):
    hash_object = hashlib.md5(str_to_hash.encode())
    md5_hash = hash_object.hexdigest()
    return md5_hash


def get_md5_hash(file_path, block_size=2 ** 8):
    md5 = hashlib.md5()
    f = open(file_path, 'rb')
    while True:
        data = f.read(block_size)
        if not data:
            break
        md5.update(data)
    return md5.hexdigest()


def get_sha256_hash(file_path, block_size=2 ** 8):
    sha256 = hashlib.sha256()
    f = open(file_path, 'rb')
    while True:
        data = f.read(block_size)
        if not data:
            break
        sha256.update(data)
    return sha256.hexdigest()


def get_md5_sha1_sha256_hashes(file_path, block_size=2 ** 8):
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    f = open(file_path, 'rb')
    while True:
        data = f.read(block_size)
        if not data:
            break
        md5.update(data)
        sha1.update(data)
        sha256.update(data)
    return [md5.hexdigest(), sha1.hexdigest(), sha256.hexdigest()]


def generate_random_string(length=8):
    characters = string.ascii_letters + string.digits
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string


def find_java_home_by_env():
    java_home = os.environ.get('JAVA_HOME')
    if java_home:
        return java_home
    else:
        return None


def find_java_home_by_cmd_location():
    java_cmd = 'java'
    try:
        process_output = subprocess.check_output([java_cmd, '-XshowSettings:properties', '-version'], stderr=subprocess.STDOUT, text=True).strip()
        java_path = [item.split('=', 1)[1].strip() for item in process_output.splitlines() if 'java.home' in item ][0]
        return java_path
    except:
        raise RuntimeError("'java' command was not found in the system's PATH.")


def find_jdk8_based_on_java_home(java_home):
    jdk8_home = None
    with os.scandir(os.path.dirname(java_home)) as entries:
        for entry in entries:
            path = entry.path
            if entry.is_dir() and "jdk1.8" in path:
                jdk8_home = entry.path
                break
    return jdk8_home


def find_java_and_jdk8():
    java_home = find_java_home_by_env()
    jdk8_home = None
    if java_home is None:
        java_home = find_java_home_by_cmd_location()
    if java_home is not None:
        jdk8_home = find_jdk8_based_on_java_home(java_home)
    return java_home, jdk8_home


def replace_path_separators_cross_platform(path_string):
    # Replace both forward slash / and backward slash \ with an underscore
    return re.sub(r'[\\/]', '_', path_string)


def split_array(arr, n):
    if arr is None:
        raise ValueError("Array is none and cant be divided")
    arr_size = len(arr)
    result = {k: [] for k in range(n)}
    for i in range(arr_size):
        k = i % n
        result[k].append(arr[i])
    return result


def main():
    array = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
    n = 50
    splits = split_array(array, n)
    print(splits)
    # print(find_java_and_jdk8())
    # list1 = [{'a': 1, 'b': 2}, None, {'c': 3, 'd': 4}]
    # list2 = [{'c': 3, 'd': 4}, {'e': 5, 'f': 6}, None]
    # print(diff_values(list1, list2))
    # dict1 = {'a': 1, 'b': 2}
    # dict2 = {'b': 3, 'd': 4}
    # print(diff_values(dict1, dict2))
    # print(diff_values([1, 2, 3], [3, 4, 5]))
    # print(diff_values([{'a': 1, 'b': 2}, None, {'c': 3, 'd': 4}], [{'c': 33, 'd': 4}, {'e': 5, 'f': 6}, None]))


if __name__ == "__main__":
    main()
