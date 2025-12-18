from pymate.common.tool import BaseTool
from pymate.common.command import Command
from pymate.utils import fs_utils, utils
import sys
import os
from os.path import expanduser


class ToolAspectjInstrumentation(BaseTool):

    def __init__(self, jdk17_home_dir: str = None, libs_dir: str = None, dir_to_be_woven: str = None,
                 root_dir_for_src_files: str = None, output_dir: str = None):
        java_from_jdk17 = os.path.join(jdk17_home_dir, "bin", "java")
        classpath_lib_dir = os.path.join(libs_dir, "*")
        assert dir_to_be_woven is not None
        assert root_dir_for_src_files is not None
        assert output_dir is not None
        command_cmd = [java_from_jdk17, "-cp", classpath_lib_dir, "org.aspectj.tools.ajc.Main", "-Xlint:ignore",
                       "-inpath", dir_to_be_woven, "-d", output_dir, "-source", "1.8", "-sourceroots",
                       root_dir_for_src_files]

        cmd = Command(cmd=command_cmd)
        super().__init__(name=self.__class__.__name__,
                         description="AspectjWeaver",
                         cmd=cmd, options={
                "jdk17_home_dir": jdk17_home_dir,
                "libs_dir": libs_dir,
                "dir_to_be_woven": dir_to_be_woven,
                "root_dir_for_src_files": root_dir_for_src_files,
                "output_dir": output_dir
            })
        self.jdk17_home_dir = jdk17_home_dir
        self.libs_dir = libs_dir
        self.dir_to_be_woven = dir_to_be_woven
        self.root_dir_for_src_files = root_dir_for_src_files
        self.output_dir = output_dir

    def before_exec(self):
        if not os.path.exists(self.dir_to_be_woven):
            raise RuntimeError("AspectjWeaver: input file is missing")
        if not os.path.exists(self.output_dir):
            raise RuntimeError("AspectjWeaver: output dir already exists")

    def after_exec(self):
        files = fs_utils.list_files(self.output_dir)
        if not len(files) > 1 :
            raise RuntimeError("AspectjWeaver: output dir is empty")
