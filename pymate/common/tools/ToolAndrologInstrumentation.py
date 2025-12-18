import os
from pymate.common.command import Command
from pymate.common.tool import BaseTool
from pymate.utils import fs_utils


class ToolAndrologInstrumentation(BaseTool):

    def __init__(self, androlog_jar, platform_dir, input_file, output_dir, log_identifier="ANDROLOG_ID",
                 monitor_classes=True, monitor_methods=True, monitor_statements=False, monitor_components=True):
        assert input_file is not None
        assert output_dir is not None
        self.input_file = input_file
        self.output_dir = output_dir
        self.expected_output_file = os.path.join(output_dir, fs_utils.get_file_without_parent(input_file))
        extra_options = []
        if monitor_classes:
            extra_options.append("-c")
        if monitor_methods:
            extra_options.append("-m")
        if monitor_statements:
            extra_options.append("-s")
        if monitor_components:
            extra_options.append("-cp")
        command_cmd = ["java", "-Xmx128g", "-Xms64g","-jar", androlog_jar, "-p", platform_dir, "-l", log_identifier,
                       "-o", output_dir, "-a", input_file] + extra_options
        cmd = Command(cmd=command_cmd)
        super().__init__(name=self.__class__.__name__,
                         description="Androlog",
                         cmd=cmd, options={
                "androlog_jar": androlog_jar,
                "platform_dir": platform_dir,
                "log_identifier": log_identifier,
                "output_dir": output_dir,
                "input_file": input_file,
                "monitor_classes": monitor_classes,
                "monitor_methods": monitor_methods,
                "monitor_statements": monitor_statements,
                "monitor_components": monitor_components
            })

    def before_exec(self):
        if not os.path.exists(self.input_file):
            raise RuntimeError("Androlog: input file is missing")
        if not os.path.exists(self.output_dir):
            raise RuntimeError("Androlog: output dir must exist")

    def after_exec(self):
        if not os.path.exists(self.expected_output_file):
            raise RuntimeError("Androlog: output file should exist after instrumentation")
