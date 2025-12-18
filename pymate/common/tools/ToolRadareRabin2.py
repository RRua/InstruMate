import json
import os

from pymate.common.command import Command
from pymate.common.tool import BaseTool
from pymate.utils import utils


class ToolRadareRabin2(BaseTool):

    def __init__(self, input_file=None, stdout_file=None, stderr_file=None):
        assert input_file is not None
        if utils.is_windows():
            rabin2 = "rabin2"
        else:
            rabin2 = "radare2.rabin2"
        command_cmd = [rabin2, "-j", "-g", input_file]
        cmd = Command(cmd=command_cmd)
        cmd.stdout_file = stdout_file
        cmd.stderr_file = stderr_file
        super().__init__(name=self.__class__.__name__,
                         description="RadareRabin2",
                         cmd=cmd, options={
                "input_file": input_file,
                "stdout_file": stdout_file,
                "stderr_file": stderr_file
            })
        self.input_file = input_file
        self.analysis = None

    def before_exec(self):
        if not os.path.exists(self.input_file):
            raise RuntimeError("RadareRabin2: input file is missing")

    def after_exec(self):
        if not os.path.isfile(self.cmd.stdout_file):
            raise FileNotFoundError(f"The stdout file '{self.cmd.stdout_file}' does not exist.")
        else:
            file_size = os.path.getsize(self.cmd.stdout_file)
            if file_size < 4:
                raise RuntimeError(
                    f"The stdout file '{self.cmd.stdout_file}' has a small size: {file_size} bytes. Probably an error.")
        # if os.path.isfile(self.cmd.stderr_file):
        #     file_size = os.path.getsize(self.cmd.stderr_file)
        #     if file_size > 10:
        #         raise RuntimeError(
        #             f"The err file '{self.cmd.stderr_file}' has a large size: {file_size} bytes. Probably an error.")
