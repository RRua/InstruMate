import os
from pymate.common.command import Command
from pymate.common.tool import BaseTool
from pymate.utils import fs_utils


class ToolCosmoInstrumentation(BaseTool):

    def __init__(self, cosmo_dir, jdk8_path, input_file, output_dir):
        assert input_file is not None
        assert output_dir is not None
        self.input_file = input_file
        self.output_dir = output_dir
        self.expected_output_file = os.path.join(output_dir, fs_utils.get_file_without_parent(input_file))
        classpath_jacoco_cli_jar = os.path.join(cosmo_dir, "lib", "jacococli.jar")
        java_from_jdk8 = os.path.join(jdk8_path, "bin", "java")
        command_cmd = [java_from_jdk8, "-jar", classpath_jacoco_cli_jar, "instrument", input_file,
                       "--dest", output_dir]
        cmd = Command(cmd=command_cmd)
        super().__init__(name=self.__class__.__name__,
                         description="COSMO",
                         cmd=cmd, options={
                "cosmo": cosmo_dir,
                "jdk8_path": jdk8_path,
                "input_file": input_file,
                "output_dir": output_dir
            })

    def before_exec(self):
        if not os.path.exists(self.input_file):
            raise RuntimeError("COSMO: input file is missing")

    def after_exec(self):
        if not os.path.exists(self.expected_output_file):
            raise RuntimeError("COSMO: output file should exist after instrumentation")