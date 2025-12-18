import os
from pymate.common.command import Command
from pymate.common.tool import BaseTool


class ToolZipalign(BaseTool):

    def __init__(self, tool_zipalign_path, input_file, output_file):
        align_cmd = [tool_zipalign_path, "-p", "4", input_file, output_file]
        cmd = Command(cmd=align_cmd)
        super().__init__(name=self.__class__.__name__,
                         description="zipalign.exe: Zip alignment utility. Copyright (C) 2009 The Android Open Source Project",
                         cmd=cmd, options={
                "4": "alignment in bytes, e.g. '4' provides 32-bit alignment"
            })
        self.input_file = input_file
        self.output_file = output_file

    def before_exec(self):
        if not os.path.exists(self.input_file):
            raise RuntimeError("ZipAlign: input file is missing")
        if os.path.exists(self.output_file):
            raise RuntimeError("ZipAlign: output file already exists")

    def after_exec(self):
        if not os.path.exists(self.output_file):
            raise RuntimeError("ZipAlign: output file should exist after zip alignment")
