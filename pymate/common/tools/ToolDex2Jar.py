import os
from pymate.common.command import Command
from pymate.common.tool import BaseTool
from pymate.utils.utils import is_windows

DEX2JAR_2DEX = "2dex"
DEX2JAR_2JAR = "2jar"


class ToolDex2Jar(BaseTool):

    def __init__(self, dextool_dir, mode: str, input_file, output_file):
        command_cmd = None
        if is_windows():
            self.tool_dex2jar = os.path.join(dextool_dir, "d2j-dex2jar.bat")
            self.tool_jar2dex = os.path.join(dextool_dir, "d2j-jar2dex.bat")
        else:
            self.tool_dex2jar = os.path.join(dextool_dir, "d2j-dex2jar.sh")
            self.tool_jar2dex = os.path.join(dextool_dir, "d2j-jar2dex.sh")
        if mode == DEX2JAR_2JAR:
            assert input_file is not None
            assert output_file is not None
            convert_cmd = [self.tool_dex2jar, "-f", input_file, "-o", output_file]
            command_cmd = convert_cmd
        if mode == DEX2JAR_2DEX:
            assert input_file is not None
            assert output_file is not None
            convert_cmd = [self.tool_jar2dex, "-f", input_file, "-o", output_file]
            command_cmd = convert_cmd
        if command_cmd is None:
            raise RuntimeError(f"Invalid mode: {mode}")
        cmd = Command(cmd=command_cmd)
        super().__init__(name=self.__class__.__name__,
                         description="Dex2Jar",
                         cmd=cmd, options={
                "mode": mode
            })
        self.mode = mode
        self.input_file = input_file
        self.output_file = output_file

    def before_exec(self):
        if self.mode == DEX2JAR_2JAR or self.mode == DEX2JAR_2DEX:
            if not os.path.exists(self.input_file):
                raise RuntimeError("Dex2Jar: input file is missing")
            if os.path.exists(self.output_file):
                raise RuntimeError("Dex2Jar: output file already exists")

    def after_exec(self):
        if self.mode == DEX2JAR_2JAR or self.mode == DEX2JAR_2DEX:
            if not os.path.exists(self.output_file):
                raise RuntimeError("Dex2Jar: output file should exist after conversion")


class ToolDex2JarMakeJar(ToolDex2Jar):
    def __init__(self, dextool_dir, input_file, output_file):
        super().__init__(dextool_dir=dextool_dir,
                         mode=DEX2JAR_2JAR,
                         input_file=input_file,
                         output_file=output_file)


class ToolDex2JarMakeDex(ToolDex2Jar):
    def __init__(self, dextool_dir, input_file, output_file):
        super().__init__(dextool_dir=dextool_dir,
                         mode=DEX2JAR_2DEX,
                         input_file=input_file,
                         output_file=output_file)
