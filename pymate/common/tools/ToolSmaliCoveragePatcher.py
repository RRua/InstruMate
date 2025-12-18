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


def increment_locals(input_string: str) -> str:
    pattern = r"(\s*\.locals\s+)(\d+)"

    def replace_function(match):
        prefix = match.group(1)
        number = int(match.group(2))
        incremented_number = number + 2
        return f"{prefix}{incremented_number}"

    output_string = re.sub(pattern, replace_function, input_string)
    return output_string


def clean_string(unwanted_words, input_string):
    pattern = r'\b(' + '|'.join(map(re.escape, unwanted_words)) + r')\b'
    cleaned_string = re.sub(pattern, '', input_string, flags=re.IGNORECASE)
    cleaned_string = re.sub(r'\s+', ' ', cleaned_string).strip()
    return cleaned_string


def inject_coverage_into_smali(target_smali: Path, coverage_tag="IM-COVERAGE"):
    if not target_smali or not target_smali.exists():
        return False
    text = target_smali.read_text()
    text = text.split("\n")
    idx = 0
    qtd_injections = 0
    while idx != len(text):
        line = text[idx].strip()
        if line.startswith('.method'):
            if ".locals" not in text[idx + 1]:
                idx += 1
                continue
            qtd_locals = count_locals(text[idx + 1])
            qtd_variables = count_variables(text, idx + 1)
            qtd_params = count_params(text, idx + 1)
            if (qtd_locals+qtd_variables+qtd_params) < 13:
                text[idx + 1] = increment_locals(text[idx + 1])
                coverage_msg = "passed here"
                text.insert(idx + 2,
                            "    invoke-static {v0, v1}, "
                            "Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I")
                text.insert(idx + 2,
                            f"    const-string v1, "
                            f"\"{coverage_msg}\"")
                text.insert(idx + 2,
                            f"    const-string v0, "
                            f"\"{coverage_tag}\"")
                idx = idx + 3
                qtd_injections += 1
        idx += 1
    target_smali.write_text("\n".join(text))
    return qtd_injections


class ToolSmaliCoveragePatcher(BaseTool):
    def __init__(self,
                 smali_dir=None,
                 exclude_packages=None,
                 log_tag="IM-COVERAGE"):
        super().__init__(name=self.__class__.__name__,
                         description="ToolFridaSmaliPatcher", options={
                "smali_dir": smali_dir,
                "exclude_packages": exclude_packages,
                "log_tag": log_tag
            })
        self.smali_dir = smali_dir
        if exclude_packages is None:
            self.exclude_packages = ["androidx", "android", "com.google", "kotlin", "kotlinx", "org.intellij",
                                     "org.jetbrains"]
        else:
            self.exclude_packages = exclude_packages
        self.log_tag = log_tag
        self.qtd_injections = 0

    def before_exec(self):
        pass

    def after_exec(self):
        pass

    def exec_script(self) -> (str, str):
        excluded_paths = [excluded_package.replace('.', os.sep) for excluded_package in self.exclude_packages]
        smali_files = fs_utils.list_files(self.smali_dir, extension="smali")
        for smali_file in smali_files:
            is_excluded = False
            for item in excluded_paths:
                path_to_search = os.path.join(self.smali_dir, item)
                if path_to_search in smali_file:
                    is_excluded = True
                    break
            if not is_excluded:
                qtd_file_injections = inject_coverage_into_smali(target_smali=Path(smali_file))
                self.qtd_injections = self.qtd_injections + qtd_file_injections
        return f"QTD injections: {self.qtd_injections}. Tag: {self.log_tag}", ""
