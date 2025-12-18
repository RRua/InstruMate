import os
from pymate.common.command import Command
from pymate.common.tool import BaseTool
from pymate.utils import fs_utils

MODE_DYNAMIC_CALL_GRAPH = "dynCG"


class ToolDroidfaxInstrumentation(BaseTool):

    def __init__(self, droidfax_dir, jdk8_path, mode: str, input_file, output_dir):
        assert input_file is not None
        assert output_dir is not None
        self.input_file = input_file
        self.output_dir = output_dir
        self.expected_output_file = os.path.join(output_dir, fs_utils.get_file_without_parent(input_file))
        self.mode = mode
        classpath_lib_dir = os.path.join(droidfax_dir, "libs", "*")
        classpath_android_jar = os.path.join(droidfax_dir, "libs", "android.jar")
        classpath_droidfax_jar = os.path.join(droidfax_dir, "libs", "droidfax.jar")
        java_from_jdk8 = os.path.join(jdk8_path, "bin", "java")
        if mode == MODE_DYNAMIC_CALL_GRAPH:
            command_cmd = [java_from_jdk8, "-Xmx14g", "-ea", "-cp", classpath_lib_dir, "dynCG.sceneInstr", "-w",
                           "-force-android-jar",
                           classpath_android_jar, "-cp", classpath_droidfax_jar, "-p", "cg",
                           "verbose:false,implicit-entry:true", "-p", "cg.spark",
                           "verbose:false,on-fly-cg:true,rta:false", "-d", output_dir, "-instr3rdparty",
                           "-process-dir", input_file]
        else:
            raise NotImplementedError("Not implemented")
        cmd = Command(cmd=command_cmd)
        super().__init__(name=self.__class__.__name__,
                         description="Droidfax",
                         cmd=cmd, options={
                "mode": mode,
                "droidfax_dir": droidfax_dir,
                "jdk8_path": jdk8_path,
                "input_file": input_file,
                "output_dir": output_dir
            })

    def after_exec(self):
        if not os.path.exists(self.expected_output_file):
            raise RuntimeError("Droidfax: output file should exist after instrumentation")
