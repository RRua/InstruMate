import os
import traceback
from pymate.common.tool import BaseTool
from pymate.utils import fs_utils
import xml.etree.ElementTree as ET


class ToolChangeStringResource(BaseTool):

    def __init__(self, input_dir=None, skip_modifications = False):
        super().__init__(name=self.__class__.__name__,
                         description="String Resources Editor",
                         cmd=None, options={
                "input_dir": input_dir,
            })
        self.input_dir = input_dir
        self.suffix = "-mate"
        self.key_to_change = None
        self.change_first_on_none_key = True
        self.qtd_changes = 0
        self.file_changes = []
        self.skip_modifications = skip_modifications

    def before_exec(self):
        if not os.path.exists(self.input_dir):
            raise RuntimeError("String Resources Editor: input dir is missing")
        android_manifest = os.path.join(self.input_dir, "AndroidManifest.xml")
        if not os.path.exists(android_manifest):
            raise RuntimeError("String Resources Editor: can't change resources without AndroidManifest.xml present.")

    def after_exec(self):
        if self.qtd_changes == 0 and not self.skip_modifications:
            raise RuntimeError("String Resources Editor: Couldn't find any resource to change")

    def exec_script(self) -> (str, str):
        self._select_string_key_to_be_changed()
        xml_files = fs_utils.list_files(directory_path=self.input_dir, extension='xml')
        string_resources_files = [item for item in xml_files if fs_utils.get_file_without_parent(item) == 'strings.xml']
        changed = False
        attempt_index = 0
        max_attempts = 3
        while not changed and attempt_index < max_attempts:
            attempt_index = attempt_index + 1
            for string_xml in string_resources_files:
                changed, new_key = self._modify_selected_key(xml_path=string_xml)
                if changed:
                    break
                if new_key is not None:
                    self.key_to_change = new_key
                    break
        return f"Changed: {changed}\n" \
               f"Attempt index: {attempt_index}\n" \
               f"Selected key: {self.key_to_change}", ""

    def _select_string_key_to_be_changed(self):
        android_manifest = os.path.join(self.input_dir, "AndroidManifest.xml")
        try:
            tree = ET.parse(android_manifest)
        except Exception as e:
            tb_exception = traceback.format_exc()
            self.logger.debug(tb_exception)
            raise
        namespaces = dict([node for _, node in
                           ET.iterparse(android_manifest,
                                        events=["start-ns"])])
        for ns in namespaces:
            ET.register_namespace(ns, namespaces[ns])

        if "android" not in namespaces:
            android_namespace = 'http://schemas.android.com/apk/res/android'
            ET.register_namespace('android', android_namespace)
            android_prefix = '{' + android_namespace + '}'
        else:
            android_prefix = "{" + namespaces["android"] + "}"

        selected_key_to_change = None
        for el in tree.findall("application"):
            app_label = el.get(android_prefix + "label")
            if app_label is not None and app_label.startswith("@string/"):
                selected_key_to_change = app_label
                break
            else:
                for act in el.findall("activity"):
                    act_label = act.get(android_prefix+"label")
                    if act_label is not None and act_label.startswith("@string/"):
                        selected_key_to_change = act_label
                        break
        if selected_key_to_change is not None:
            self.key_to_change = selected_key_to_change.split('/')[1]

    def _modify_string_value(self, input_string):
        suffix = self.suffix
        suffix_size = len(suffix)
        n = len(input_string)
        if n < suffix_size:
            return input_string + suffix
        else:
            modified_string = input_string[:(-1*suffix_size)] + suffix
            return modified_string

    def _modify_selected_key(self, xml_path):
        tree = ET.parse(xml_path)
        root = tree.getroot()
        changed = False
        # alias check
        new_key = None
        modification = {"xml_path": xml_path}
        for string_element in root.findall('string'):
            if self.key_to_change is not None:
                if string_element.get('name') == self.key_to_change:
                    if string_element.text.startswith("@string/"):
                        new_key = string_element.text.split('/')[1]
                        break
                    else:
                        modification["old_value"] = string_element.text
                        string_element.text = self._modify_string_value(string_element.text)
                        modification["new_value"] = string_element.text
                        self.qtd_changes = self.qtd_changes+1
                        changed = True
                        break
            else:
                if self.change_first_on_none_key:
                    if len(string_element.text) > len(self.suffix) and not string_element.text.startswith("@string/"):
                        self.key_to_change = string_element.get('name')
                        modification["old_value"] = string_element.text
                        string_element.text = self._modify_string_value(string_element.text)
                        modification["new_value"] = string_element.text
                        self.qtd_changes = self.qtd_changes + 1
                        changed = True
                        break
        if changed:
            self.file_changes.append(modification)
            if not self.skip_modifications:
                tree.write(xml_path, encoding='utf-8', xml_declaration=True)
        return changed, new_key


def main():
    input_dir = ".\\input\\apk\\random\\reference-app\\"
    tool = ToolChangeStringResource(input_dir=input_dir, new_name_prefix=None, new_icon=None)
    tool.execute()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG)
    main()