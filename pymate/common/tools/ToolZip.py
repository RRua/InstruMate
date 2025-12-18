import os
import zipfile
from pymate.common.tool import BaseTool
from pymate.utils import utils, fs_utils

ZIPTOOL_UNPACK = "unpack"
ZIPTOOL_REPACK = "repack"


class ToolZip(BaseTool):
    def __init__(self, mode: str, input_file: str = None, input_dir: str = None, output_file: str = None,
                 output_dir: str = None, not_compress_files: list = None, fail_on_ms_windows_overwrite=True,
                 merge_with_existing_outputdir=False, fail_on_merge_overwrite=False):
        super().__init__(name=self.__class__.__name__,
                         description="ZipTool", options={
                "mode": mode,
                "input_file": input_file,
                "input_dir": input_dir,
                "output_file": output_file,
                "output_dir": output_dir,
                "fail_on_ms_windows_overwrite": fail_on_ms_windows_overwrite,
                "merge_with_existing_outputdir": merge_with_existing_outputdir,
                "fail_on_merge_overwrite": fail_on_merge_overwrite
            })
        if mode == ZIPTOOL_UNPACK:
            assert input_file is not None
            assert output_dir is not None
        if mode == ZIPTOOL_REPACK:
            assert input_dir is not None
            assert output_file is not None
        self.mode = mode
        self.input_file = input_file
        self.input_dir = input_dir
        self.output_file = output_file
        self.output_dir = output_dir
        self.extracted_file_list = None
        self.fail_on_ms_windows_overwrite = fail_on_ms_windows_overwrite
        self.ms_windows_case_insensitive_files = None
        self.not_compress_files = not_compress_files
        self.merge_with_existing_outputdir = merge_with_existing_outputdir
        self.fail_on_merge_overwrite = fail_on_merge_overwrite

    def before_exec(self):
        if self.mode == ZIPTOOL_UNPACK:
            if not os.path.exists(self.input_file):
                raise RuntimeError("ZipUnpack: input file is missing")
            if os.path.exists(self.output_dir) and not self.merge_with_existing_outputdir:
                raise RuntimeError("ZipUnpack: output dir must not exist")
        if self.mode == ZIPTOOL_REPACK:
            if not os.path.exists(self.input_dir):
                raise RuntimeError("ZipRepack: input dir is missing")
            if os.path.exists(self.output_file):
                raise RuntimeError("ZipRepack: output file must not exist")

    def after_exec(self):
        if self.mode == ZIPTOOL_UNPACK:
            if not os.path.exists(self.output_dir):
                raise RuntimeError("ZipUnpack: output dir is missing")
        if self.mode == ZIPTOOL_REPACK:
            if not os.path.exists(self.output_file):
                raise RuntimeError("ZipRepack: output file is missing")

    def exec_script(self) -> (str, str):
        if self.mode == ZIPTOOL_UNPACK:
            extracted_file_list = []
            case_insensitive_file_list = set()
            ms_windows_case_insensitive_files = []
            with zipfile.ZipFile(self.input_file, 'r') as zip_ref:
                for file_info in zip_ref.infolist():
                    extracted_file_path = os.path.join(self.output_dir, file_info.filename)
                    if self.merge_with_existing_outputdir and self.fail_on_merge_overwrite and os.path.exists(
                            extracted_file_path):
                        raise RuntimeError(
                            f"Merge with zip unpack will overwrite existing data. File {extracted_file_path}")
                    zip_ref.extract(file_info, self.output_dir)
                    extracted_file_list.append(extracted_file_path)
                    if utils.is_windows() and extracted_file_path.lower() in case_insensitive_file_list:
                        ms_windows_case_insensitive_files.append(extracted_file_path.lower())
                    case_insensitive_file_list.add(extracted_file_path.lower())
            self.extracted_file_list = extracted_file_list
            self.ms_windows_case_insensitive_files = ms_windows_case_insensitive_files
            if self.fail_on_ms_windows_overwrite and len(ms_windows_case_insensitive_files) > 1:
                raise RuntimeError(f"Unzip operation had overwritten files {str(ms_windows_case_insensitive_files)}")
            return "", ""
        if self.mode == ZIPTOOL_REPACK:
            with zipfile.ZipFile(self.output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in fs_utils.list_files(self.input_dir):
                    relative_path = os.path.relpath(file, self.input_dir)
                    file_ext = fs_utils.get_file_extension(file)
                    if relative_path in self.not_compress_files or file_ext in self.not_compress_files:
                        zipf.write(file, relative_path, compress_type=zipfile.ZIP_STORED)
                    else:
                        zipf.write(file, relative_path, compress_type=zipfile.ZIP_DEFLATED)
        return "", ""


class ToolZipUnpack(ToolZip):
    def __init__(self, input_file, output_dir, fail_on_ms_windows_overwrite=True, merge_with_existing_outputdir=False,
                 fail_on_merge_overwrite=False):
        super().__init__(mode=ZIPTOOL_UNPACK, input_file=input_file, output_dir=output_dir,
                         fail_on_ms_windows_overwrite=fail_on_ms_windows_overwrite,
                         merge_with_existing_outputdir=merge_with_existing_outputdir,
                         fail_on_merge_overwrite=fail_on_merge_overwrite)


class ToolZipRepack(ToolZip):
    def __init__(self, input_dir, output_file, not_compress_files=[]):
        super().__init__(mode=ZIPTOOL_REPACK, input_dir=input_dir, output_file=output_file,
                         not_compress_files=not_compress_files)
