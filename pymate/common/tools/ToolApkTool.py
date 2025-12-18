import os
from pymate.common.command import Command
from pymate.common.tool import BaseTool
from pymate.utils import fs_utils

APK_TOOL_MODE_UNPACK = "unpack"
APK_TOOL_MODE_REPACK = "repack"
# APK_TOOL_SMALI_SKIP = "-no-src"  # skip all smali
# APK_TOOL_SMALI_ALL = ""  # smali all
# APK_TOOL_SMALI_MAIN_CLS = "-only-main-classes"  # smali only main classes
# APK_TOOL_RESOURCES_SKIP = "-no-res"  # skip resources
# APK_TOOL_RESOURCES_ALL = ""  # decode all resources

#
# skip the extraction of the assets directory
# This option is useful when the assets (such as raw files, fonts, etc.) are not relevant
# APK_TOOL_ASSETS_SKIP = "-no-assets"
# APK_TOOL_ASSETS_ALL = ""


class ToolApkTool(BaseTool):
    def __init__(self, tool_path=None,
                 mode: str = None,
                 input_file=None,
                 input_dir=None,
                 output_dir=None,
                 output_file=None,
                 decode_smali=False,
                 decode_smali_only_main_classes=False,
                 decode_resources=False,
                 decode_resources_only_manifest=False,
                 decode_assets=False):
        command_cmd = None
        self.mode = mode
        if mode == APK_TOOL_MODE_UNPACK:
            assert input_file is not None
            assert output_dir is not None
            unpack_cmd = ["java", "-jar", tool_path, "d", "-f"]
            if decode_smali:
                if decode_smali_only_main_classes:
                    unpack_cmd.append("-only-main-classes")
            else:
                unpack_cmd.append("-no-src")
            if decode_resources:
                if decode_resources_only_manifest:
                    unpack_cmd.append("-force-manifest")
            else:
                unpack_cmd.append("-no-res")
            if not decode_assets:
                unpack_cmd.append("-no-assets")
            unpack_cmd.append("-o")
            unpack_cmd.append(output_dir)
            unpack_cmd.append(input_file)
            command_cmd = unpack_cmd
        if mode == APK_TOOL_MODE_REPACK:
            assert input_dir is not None
            assert output_file is not None
            repack_cmd = ["java", "-jar", tool_path, "b", "-f", "--use-aapt2", "-o", output_file,
                          input_dir]
            command_cmd = repack_cmd
        if command_cmd is None:
            raise RuntimeError(f"Invalid mode: {mode}")
        cmd = Command(cmd=command_cmd)
        super().__init__(name=self.__class__.__name__,
                         description="ApkTool",
                         cmd=cmd, options={
                "mode": mode,
                "input_file": input_file,
                "input_dir": input_dir,
                "output_dir": output_dir,
                "output_file": output_file,
                "decode_smali": decode_smali,
                "decode_smali_only_main_classes": decode_smali_only_main_classes,
                "decode_resources": decode_resources,
                "decode_resources_only_manifest": decode_resources_only_manifest,
                "decode_assets": decode_assets
            })
        self.mode = mode
        self.input_file = input_file
        self.input_dir = input_dir
        self.output_file = output_file
        self.output_dir = output_dir

    def before_exec(self):
        if self.mode == APK_TOOL_MODE_UNPACK:
            if not os.path.exists(self.input_file):
                raise RuntimeError("ApkTool: input file is missing")
            if not os.path.exists(self.output_dir):
                raise RuntimeError("ApkTool: output dir is missing")
        if self.mode == APK_TOOL_MODE_REPACK:
            if not len(fs_utils.list_files(self.input_dir)) > 1:
                raise RuntimeError("ApkTool: input dir is empty before repack - files should exist there")

    def after_exec(self):
        if self.mode == APK_TOOL_MODE_UNPACK:
            if not os.path.exists(self.output_dir):
                raise RuntimeError("ApkTool: should exist")
            if not len(fs_utils.list_files(self.output_dir)) > 1:
                raise RuntimeError("ApkTool: output dir is empty after unpack")
            if self.cmd is not None and self.cmd.stderr is not None:
                if "End of chunk hit" in self.cmd.stderr:
                    raise RuntimeError(f"ApkTool failed in the middle of the process: {self.cmd.stderr}")
        if self.mode == APK_TOOL_MODE_REPACK:
            if not os.path.exists(self.output_file):
                raise RuntimeError("ApkTool: file was not repackaged sinc destfile is missing")


class ToolApkToolUnpack(ToolApkTool):
    def __init__(self, tool_path, input_file, output_dir, decode_smali=False,
                 decode_smali_only_main_classes=False,
                 decode_resources=False,
                 decode_resources_only_manifest=False,
                 decode_assets=False):
        super().__init__(tool_path=tool_path,
                         mode=APK_TOOL_MODE_UNPACK,
                         input_file=input_file,
                         output_dir=output_dir,
                         decode_smali=decode_smali,
                         decode_smali_only_main_classes=decode_smali_only_main_classes,
                         decode_resources=decode_resources,
                         decode_resources_only_manifest=decode_resources_only_manifest,
                         decode_assets=decode_assets)


class ToolApkToolRepack(ToolApkTool):
    def __init__(self, tool_path, input_dir, output_file):
        super().__init__(tool_path=tool_path,
                         mode=APK_TOOL_MODE_REPACK,
                         input_dir=input_dir,
                         output_file=output_file)
