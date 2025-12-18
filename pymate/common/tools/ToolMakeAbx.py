import os
from pymate.common.command import Command
from pymate.common.tool import BaseTool


class ToolMakeAbx(BaseTool):
    def __init__(self, tool_path, input_file, output_file):
        sign_cmd = ["java", "-jar", tool_path, input_file, output_file]
        cmd = Command(cmd=sign_cmd)
        super().__init__(name=self.__class__.__name__,
                         description="MakeAbx.jar: Android bits",
                         cmd=cmd, options={
            })
        self.input_file = input_file
        self.output_file = output_file

    def before_exec(self):
        if not os.path.exists(self.input_file):
            raise RuntimeError("MakeAbx.jar: input file is missing")
        if os.path.exists(self.output_file):
            raise RuntimeError("MakeAbx.jar: output file already exists")

    def after_exec(self):
        if not os.path.exists(self.output_file):
            raise RuntimeError("MakeAbx.jar: output file should exist")