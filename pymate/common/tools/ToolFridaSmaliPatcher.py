from pymate.common.tool import BaseTool
import os
import json
import logging
from pathlib import Path
from pymate.utils import fs_utils
import re


def count_locals(input_string: str) -> int:
    pattern = r"(\s*\.locals\s+)(\d+)"
    compiled_pattern = re.compile(pattern)
    match = compiled_pattern.search(input_string)
    if match:
        prefix = match.group(1)
        number = int(match.group(2))
        return number
    return -1


def find_class_file(base_dir: str, class_name: str) -> Path:
    class_file_path = class_name.replace('.', os.sep) + ".smali"
    full_path = Path(base_dir) / class_file_path
    if full_path.exists():
        return full_path
    else:
        return None


def increment_locals(input_string: str) -> str:
    pattern = r"(\s*\.locals\s+)(\d+)"

    def replace_function(match):
        prefix = match.group(1)
        number = int(match.group(2))
        incremented_number = number + 1
        return f"{prefix}{incremented_number}"

    output_string = re.sub(pattern, replace_function, input_string)
    return output_string


def count_variables(method_body, position):
    pattern = r'\bv\d+\b'
    idx = position
    max_n = 0
    while idx != len(method_body):
        line = method_body[idx]
        if line.startswith(".end method"):
            break
        matches = re.findall(pattern, line)
        for match in matches:
            number = int(re.search(r'\d+', match).group())
            if max_n is None or number > max_n:
                max_n = number
        idx = idx + 1
    return max_n


def count_params(method_body, position):
    pattern = r'\bp\d+\b'
    idx = position
    max_n = 0
    while idx != len(method_body):
        line = method_body[idx]
        if line.startswith(".end method"):
            break
        matches = re.findall(pattern, line)
        for match in matches:
            number = int(re.search(r'\d+', match).group())
            if max_n is None or number > max_n:
                max_n = number
        idx = idx + 1
    return max_n


def inject_into_smali(target_smali: Path, load_library_name: str):
    logger = logging.getLogger("FridaGadget_change_smali")
    logger.debug('Searching for the main activity in the smali files')

    if not target_smali or not target_smali.exists():
        return False

    logger.debug("Found the main activity at '%s'", str(target_smali))
    text = target_smali.read_text()

    text = text.replace(
        "invoke-virtual {v0, v1}, Ljava/lang/Runtime;->exit(I)V", "")
    text = text.split("\n")

    logger.debug(
        'Locating the entrypoint method and injecting the loadLibrary code')
    status = False
    entrypoints = ["constructor <init>"]
    for entrypoint in entrypoints:
        idx = 0
        while idx != len(text):
            line = text[idx].strip()
            if line.startswith('.method') and entrypoint in line:
                if ".locals" not in text[idx + 1]:
                    idx += 1
                    continue
                qtd_locals = count_locals(text[idx + 1])
                if qtd_locals == 0:
                    text[idx + 1] = increment_locals(text[idx + 1])
                    if load_library_name.startswith('lib'):
                        load_library_name = load_library_name[3:]
                    text.insert(idx + 2,
                                "    invoke-static {v0}, "
                                "Ljava/lang/System;->loadLibrary(Ljava/lang/String;)V")
                    text.insert(idx + 2,
                                f"    const-string v0, "
                                f"\"{load_library_name}\"")
                    status = True
                    break
            idx += 1
        if status:
            break

    if not status:
        return False

    # Replace the smali file with the new one
    target_smali.write_text("\n".join(text))
    return True


def upload_frida(lib_dir: str, archs: list, js_file_path: str, library_name):
    config_file_name = f"lib{library_name}.config.so"
    script_file_name = f"lib{library_name}.script.so"
    lib_file_name = f"lib{library_name}.so"
    #with open(js_file_path, "r", encoding="utf-8") as js_file:
    #    js_content = js_file.read()
    # "path": "/data/local/tmp/script.js",
    config = {
        "interaction": {
            "type": "script",
            "path": script_file_name,
            "on_load": "resume"
        }
    }
    for arch in archs:
        lib_file = archs[arch]
        dest_dir = os.path.join(lib_dir, arch)
        dest_lib_file = os.path.join(dest_dir, lib_file_name)
        dest_script_file = os.path.join(dest_dir, script_file_name)
        dest_config_file = os.path.join(dest_dir, config_file_name)
        fs_utils.copy_file(lib_file, dest_lib_file)
        fs_utils.copy_file(js_file_path, dest_script_file)
        with open(dest_config_file, 'w', encoding='utf-8') as config_file:
            json.dump(config, config_file, indent=4)


class ToolFridaSmaliPatcher(BaseTool):
    def __init__(self,
                 smali_dir= None,
                 lib_dir= None,
                 js_file_path= None,
                 new_library_name = None,
                 target_smali_files = None,
                 archs = None,
                 maximize_injection=True,
                 upload_lib=True):
        super().__init__(name=self.__class__.__name__,
                         description="ToolFridaSmaliPatcher", options={
                "smali_dir": smali_dir,
                "lib_dir": lib_dir,
                "js_file_path": js_file_path,
                "new_library_name": new_library_name,
                "target_smali_files": str(target_smali_files),
                "maximize_injection": maximize_injection,
                "archs": archs,
                "upload_lib": upload_lib
            })
        self.smali_dir = smali_dir
        self.lib_dir = lib_dir
        self.js_file_path = js_file_path
        self.new_library_name = new_library_name
        self.target_smali_files = target_smali_files
        self.maximize_injection = maximize_injection
        self.archs = archs
        self.qtd_injections = 0
        self.upload_lib = upload_lib

    def before_exec(self):
        pass

    def after_exec(self):
        pass

    def exec_script(self) -> (str, str):
        for injectable in self.target_smali_files:
            file_to_inject = find_class_file(base_dir=self.smali_dir, class_name=injectable)
            if file_to_inject is not None:
                success = inject_into_smali(target_smali=file_to_inject, load_library_name=self.new_library_name)
                if success:
                    self.qtd_injections = self.qtd_injections + 1
                    if not self.maximize_injection:
                        break
        if self.upload_lib:
            upload_frida(lib_dir=self.lib_dir, archs=self.archs, js_file_path=self.js_file_path,
                         library_name=self.new_library_name)
        return f"QTD injections: {self.qtd_injections}. Uploaded lib: {self.upload_lib}", ""
