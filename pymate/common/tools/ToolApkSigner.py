import os
from pymate.common.command import Command
from pymate.common.tool import BaseTool


class ToolApkSigner(BaseTool):

    def __init__(self, tool_path, apk_signer_key, apksigner_cert, input_file, output_file, key_alias="CERT"):
        sign_cmd = ["java", "-jar", tool_path, "sign", "--key", apk_signer_key,
                    "--cert", apksigner_cert, "--ks-key-alias", key_alias,
                    "--out", output_file, input_file]
        cmd = Command(cmd=sign_cmd)
        super().__init__(name=self.__class__.__name__,
                         description="ApkSigner.jar: Android Studio",
                         cmd=cmd, options={
            })
        self.input_file = input_file
        self.output_file = output_file

    def before_exec(self):
        if not os.path.exists(self.input_file):
            raise RuntimeError("ApkSigner.jar: input file is missing")
        if os.path.exists(self.output_file):
            raise RuntimeError("ApkSigner.jar: output file already exists")

    def after_exec(self):
        if not os.path.exists(self.output_file):
            raise RuntimeError("ApkSigner.jar: output file should exist after signature")
