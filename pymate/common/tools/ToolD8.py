import os
from pymate.common.command import Command
from pymate.common.tool import BaseTool


class ToolD8(BaseTool):
    def __init__(self, jdk17_home, tool_path=None, input_file=None, input_files=None, output_dir=None, android_sdk_jar=None, min_sdk_api=None):
        java_bin = os.path.join('/opt/java/jdk-17.0.11/', 'bin', 'java')
        command_cmd = [java_bin, "-Xmx12g", "-Xss1m", "-cp", tool_path, "com.android.tools.r8.D8",
                       "--release", "--lib",
                       android_sdk_jar, "--min-api", min_sdk_api, "--output", output_dir]
        if input_file is not None:
            command_cmd.append(input_file)
        if input_files is not None:
            for item in input_files:
                command_cmd.append(item)
        cmd = Command(cmd=command_cmd)
        super().__init__(name=self.__class__.__name__,
                         description="ToolD8",
                         cmd=cmd, options={
                "jdk17_home": jdk17_home,
                "tool_path": tool_path,
                "input_file": input_file,
                "input_files": input_files,
                "android_sdk_jar": android_sdk_jar,
                "min_sdk_api": min_sdk_api,
                "output_dir": output_dir
            })
        self.jdk17_home = jdk17_home
        self.tool_path = tool_path
        self.input_file = input_file
        self.android_sdk_jar = android_sdk_jar
        self.min_sdk_api = min_sdk_api
        self.output_dir = output_dir

    def before_exec(self):
        if not os.path.exists(self.input_file):
            raise RuntimeError("ToolD8: input file is missing")
        if not os.path.exists(self.output_dir):
            raise RuntimeError(f"ToolD8: output {self.output_dir} does not exist")

    def after_exec(self):
        pass
