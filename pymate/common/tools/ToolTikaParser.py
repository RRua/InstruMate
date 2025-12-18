import os
from pymate.common.command import Command
from pymate.common.tool import BaseTool


class ToolTikaParser(BaseTool):
    def __init__(self, tool_path, input_dir, output_dir):
        cmd = ["java", "-jar", tool_path, "-i", input_dir, "-o", output_dir, "-J"]
        cmd = Command(cmd=cmd)
        super().__init__(name=self.__class__.__name__,
                         description="ApacheTika Parser",
                         cmd=cmd, options={
                            "-J": "-J  or --jsonRecursive"
                            })
        self.input_dir = input_dir
        self.output_dir = output_dir

    def before_exec(self):
        if not os.path.exists(self.input_dir):
            raise RuntimeError("TikaParser: input dir is missing")
        if os.path.exists(self.output_dir):
            raise RuntimeError("TikaParser: output dir must not exist")

    def after_exec(self):
        if not os.path.exists(self.output_dir):
            raise RuntimeError("TikaParser: output dir is missing")
