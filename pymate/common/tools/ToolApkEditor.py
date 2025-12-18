import os
from pymate.common.command import Command
from pymate.common.tool import BaseTool

APK_EDITOR_MODE_UNPACK = "unpack"
APK_EDITOR_MODE_REPACK = "repack"
APK_EDITOR_MODE_MERGE = "merge"


class ToolApkEditor(BaseTool):

    def __init__(self, tool_path=None, mode: str = None, input_file=None, input_dir=None, output_dir=None,
                 output_file=None, skip_smali=True, skip_resource_decode=True):
        command_cmd = None
        if mode == APK_EDITOR_MODE_UNPACK:
            assert input_file is not None
            assert output_dir is not None
            unpack_cmd = ["java", "-jar", tool_path, "decode", "-t", ("raw" if skip_resource_decode else "xml"), "-f"]
            if skip_smali:
                unpack_cmd = unpack_cmd + ["-dex"]
            unpack_cmd = unpack_cmd + ["-i", input_file, "-o", output_dir]
            command_cmd = unpack_cmd
        if mode == APK_EDITOR_MODE_REPACK:
            assert input_dir is not None
            assert output_file is not None
            repack_cmd = ["java", "-jar", tool_path, "b", "-f", "-no-cache", "-i", input_dir,
                          "-o", output_file]
            command_cmd = repack_cmd
        if mode == APK_EDITOR_MODE_MERGE:
            assert input_dir is not None
            assert output_file is not None
            command_cmd = ["java", "-jar", tool_path, "merge", "-i", input_dir, "-o", output_file]
        if command_cmd is None:
            raise RuntimeError(f"Invalid mode: {mode}")
        cmd = Command(cmd=command_cmd)
        super().__init__(name=self.__class__.__name__,
                         description="ApkEditor",
                         cmd=cmd, options={
                "mode": mode,
            })
        self.mode = mode
        self.input_file = input_file
        self.input_dir = input_dir
        self.output_file = output_file
        self.output_dir = output_dir

    def before_exec(self):
        if self.mode == APK_EDITOR_MODE_UNPACK:
            if not os.path.exists(self.input_file):
                raise RuntimeError("ApkEditor: input file is missing")
            if os.path.exists(self.output_dir):
                raise RuntimeError("ApkEditor: output dir already exists")
        if self.mode == APK_EDITOR_MODE_REPACK:
            if not os.path.exists(self.input_dir):
                raise RuntimeError("ApkEditor: input dir is missing")
            if os.path.exists(self.output_file):
                raise RuntimeError("ApkEditor: output file already exists")
        if self.mode == APK_EDITOR_MODE_MERGE:
            if not os.path.exists(self.input_dir):
                raise RuntimeError("ApkEditor: merge input dir is missing")
            if os.path.exists(self.output_file):
                raise RuntimeError("ApkEditor: merge output file already exists")

    def after_exec(self):
        if self.mode == APK_EDITOR_MODE_UNPACK:
            if not os.path.exists(self.output_dir):
                raise RuntimeError("ApkEditor: output dir should exist after unpack")
        if self.mode == APK_EDITOR_MODE_REPACK:
            if not os.path.exists(self.output_file):
                raise RuntimeError("ApkEditor: output file should exist after repack")
        if self.mode == APK_EDITOR_MODE_MERGE:
            if not os.path.exists(self.output_file):
                raise RuntimeError("ApkEditor: merged file is missing")


class ToolApkEditorUnpack(ToolApkEditor):
    def __init__(self, tool_path, input_file, output_dir, skip_smali_decoding, skip_resources_decoding):
        super().__init__(tool_path=tool_path,
                         mode=APK_EDITOR_MODE_UNPACK,
                         input_file=input_file,
                         output_dir=output_dir,
                         skip_smali=skip_smali_decoding,
                         skip_resource_decode=skip_resources_decoding)


# class ToolApkEditorUnpackSkipSmali(ToolApkEditor):
#     def __init__(self, tool_path, input_file, output_dir):
#         super().__init__(tool_path=tool_path,
#                          mode=APK_EDITOR_MODE_UNPACK,
#                          input_file=input_file,
#                          output_dir=output_dir,
#                          skip_smali=True)
#
#
# class ToolApkEditorUnpackSmali(ToolApkEditor):
#     def __init__(self, tool_path, input_file, output_dir):
#         super().__init__(tool_path=tool_path,
#                          mode=APK_EDITOR_MODE_UNPACK,
#                          input_file=input_file,
#                          output_dir=output_dir,
#                          skip_smali=False)


class ToolApkEditorRepack(ToolApkEditor):
    def __init__(self, tool_path, input_dir, output_file):
        super().__init__(tool_path=tool_path,
                         mode=APK_EDITOR_MODE_REPACK,
                         input_dir=input_dir,
                         output_file=output_file,
                         skip_smali=False)


class ToolApkEditorMerge(ToolApkEditor):
    def __init__(self, tool_path, input_dir, output_file):
        super().__init__(tool_path=tool_path,
                         mode=APK_EDITOR_MODE_MERGE,
                         input_dir=input_dir,
                         output_file=output_file)


def main():
    tool_path = ".\\tools\\misc\\APKEditor.jar"
    input_file = ".\\input\\apk\\whatsapp.apk"
    output_dir = ".\\tmp\\apk_editor_skip_smali_whatsapp"
    from pymate.utils.fs_utils import destroy_dir_files
    destroy_dir_files(output_dir)
    unpackSkipSmali = ToolApkEditorUnpackSkipSmali(tool_path=tool_path, input_file=input_file, output_dir=output_dir)
    unpackSkipSmali.execute()

    tool_path = ".\\tools\\misc\\APKEditor.jar"
    input_file = ".\\input\\apk\\whatsapp.apk"
    output_dir = ".\\tmp\\apk_editor_with_smali_whatsapp"
    from pymate.utils.fs_utils import destroy_dir_files
    destroy_dir_files(output_dir)
    unpackSmali = ToolApkEditorUnpackSmali(tool_path=tool_path, input_file=input_file, output_dir=output_dir)
    unpackSmali.execute()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG)
    main()
