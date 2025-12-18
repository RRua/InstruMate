import os
import traceback
from pymate.common.tool import BaseTool
from pymate.utils import fs_utils
import xml.etree.ElementTree as ET


class ToolRevealPasswordFields(BaseTool):

    def __init__(self, input_dir=None, skip_modifications = False):
        super().__init__(name=self.__class__.__name__,
                         description="Reveal Password Fields",
                         cmd=None, options={
                "input_dir": input_dir,
            })
        self.input_dir = input_dir
        self.qtd_changes = 0
        self.files_changed = []
        self.skip_modifications = skip_modifications

    def before_exec(self):
        if not os.path.exists(self.input_dir):
            raise RuntimeError("Reveal Password Fields: input dir is missing")

    def after_exec(self):
        if len(self.files_changed) == 0 and not self.skip_modifications:
            raise RuntimeError("Reveal Password Fields: No password field was changed")

    def exec_script(self) -> (str, str):
        xml_files = fs_utils.list_files(directory_path=self.input_dir, extension='xml')
        for xml_file in xml_files:
            if "layout" in xml_file:
                self.reveal_passwords(xml_path=xml_file)
        return "", ""

    def reveal_passwords(self, xml_path):
        try:
            tree = ET.parse(xml_path)
        except Exception as e:
            tb_exception = traceback.format_exc()
            self.logger.debug(tb_exception)
            return
        namespaces = dict([node for _, node in
                           ET.iterparse(xml_path,
                                        events=["start-ns"])])
        for ns in namespaces:
            ET.register_namespace(ns, namespaces[ns])

        if "android" not in namespaces:
            android_namespace = 'http://schemas.android.com/apk/res/android'
            ET.register_namespace('android', android_namespace)
            android_prefix = '{' + android_namespace + '}'
        else:
            android_prefix = "{" + namespaces["android"] + "}"
        root = tree.getroot()
        xml_modified = False
        for elem in root.iter():
            input_type = elem.get(android_prefix + 'inputType')
            if input_type is not None and "password" in input_type.lower():
                elem.set(android_prefix + 'inputType', 'text')
                xml_modified = True
        if xml_modified:
            if not self.skip_modifications:
                tree.write(xml_path)
            self.files_changed.append(xml_path)

def main():
    input_dir = ".\\input\\apk\\random\\reference-app\\"
    tool = ToolRevealPasswordFields(input_dir=input_dir)
    tool.execute()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG)
    main()
