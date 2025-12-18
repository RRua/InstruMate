from pymate.common.tool import BaseTool
from pymate.common.command import Command
from pymate.utils import fs_utils, utils
import sys
import os
from os.path import expanduser


class ToolACVTool(BaseTool):
    def __init__(self, tool_path=None, input_file=None, output_dir=None, aapt_path=None, zipalign_path=None,
                 adb_path=None, apksigner_path=None, acvpatcher_path=None):
        python_executable = sys.executable
        tool_entry = os.path.join(tool_path, "main.py")
        command_cmd = [python_executable, tool_entry, "instrument", input_file, "--wd", output_dir, "--granularity", "method"]
        cmd = Command(cmd=command_cmd)
        super().__init__(name=self.__class__.__name__,
                         description="ACVTool",
                         cmd=cmd, options={
                "input_file": input_file,
                "output_dir": output_dir
            })
        self.input_file = input_file
        self.output_dir = output_dir
        self.tool_path = tool_path
        self.aapt_path = aapt_path
        self.zipalign_path = zipalign_path
        self.adb_path = adb_path
        self.apksigner_path = apksigner_path
        self.acvpatcher_path = acvpatcher_path
        self.create_config()

    def create_config(self):
        dir_path = os.path.join(expanduser("~"), 'acvtool')
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        config = {
            "AAPT": self.aapt_path,
            "ZIPALIGN": self.zipalign_path,
            "ADB": self.adb_path,
            "APKSIGNER": self.apksigner_path,
            "ACVPATCHER": self.acvpatcher_path
        }
        utils.write_dict_as_json(json_dict=config, base_dir=dir_path, file_name='config.json', overwrite_existing=True)

    def before_exec(self):
        if not os.path.exists(self.input_file):
            raise RuntimeError("ACVTool: input file is missing")

    def after_exec(self):
        created_app = fs_utils.list_files(self.output_dir)
        created_app = [item for item in created_app if fs_utils.get_file_extension(item) == '.apk']
        assert len(created_app) == 1
