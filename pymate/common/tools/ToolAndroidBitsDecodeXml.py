import os
from pymate.common.tools.android_bits_ccl_abx import AbxReader
from pymate.common.tool import BaseTool
from pymate.utils import fs_utils
import xml.etree.ElementTree as etree


class ToolAndroidBitsDecodeXml(BaseTool):
    def __init__(self, input_file: str = None, create_backup=False, multi_root_xml = False, auto_detect_multiroot=True):
        assert input_file is not None
        super().__init__(name=self.__class__.__name__,
                         description="AndroidBits Decode", options={
                "input_file": input_file,
                "create_backup": create_backup
            })
        self.input_file = input_file
        self.multi_root_xml = multi_root_xml
        self.auto_detect_multiroot = auto_detect_multiroot

    def before_exec(self):
        if not os.path.exists(self.input_file):
            raise RuntimeError("AndroidBits Decode: input file is missing")

    def after_exec(self):
        if not os.path.exists(self.input_file):
            raise RuntimeError("AndroidBits Decode: input file is missing and could not be edited")

    def exec_script(self) -> (str, str):
        with open(self.input_file, "rb") as f:
            reader = AbxReader(f)
            multi_root = self.multi_root_xml
            if self.auto_detect_multiroot:
                file_name = fs_utils.get_file_without_parent(self.input_file)
                if file_name in ["AndroidManifest.xml"]:
                    multi_root = False
                if file_name in ["settings_secure.xml"]:
                    multi_root = True
            doc = reader.read(is_multi_root=multi_root)
            doc_converted = etree.tostring(doc.getroot()).decode()
        if doc_converted is not None:
            with open(self.input_file, "wb") as fh:
                fh.write(doc_converted.encode("utf-8"))
        else:
            raise RuntimeError(f"Failed to convert binary xml {self.input_file}")
        return "", ""