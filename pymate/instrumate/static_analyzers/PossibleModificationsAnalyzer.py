import logging
import os

from pymate.common.app import App
from pymate.common.tools.ToolApkTool import ToolApkToolUnpack
from pymate.common.tools.ToolChangeIconResource import ToolChangeIconResource
from pymate.common.tools.ToolChangeStringResource import ToolChangeStringResource
from pymate.common.tools.ToolRevealPasswordFields import ToolRevealPasswordFields
from pymate.instrumate.static_analyzer import StaticAnalyzer
from pymate.utils import fs_utils


class PossibleModificationsAnalyzer(StaticAnalyzer):

    def configure(self, tmp_dir: str = None, output_dir: str = None, tools_dir: str = None, name: str = None,
                  instrumate_log=None):
        super().configure(tmp_dir=tmp_dir, output_dir=output_dir, tools_dir=tools_dir,
                          name="Possible Modifications Analyzer",
                          instrumate_log=instrumate_log)
        self.logger = logging.getLogger(self.__class__.__name__)

    def analyze_app(self, app: App):
        string_resources = []
        reveal_passwords = []
        changeable_icons = []
        self._analyze_single_apk(
            apk_path=app.get_base_pkg(),
            source_information="base", string_resources=string_resources, reveal_passwords=reveal_passwords,
            changeable_icons=changeable_icons)
        for index, item in enumerate(app.get_split_pkgs()):
            self._analyze_single_apk(
                item,
                f"split_{index}", string_resources=string_resources, reveal_passwords=reveal_passwords,
                changeable_icons=changeable_icons)
        possible_modifications_analysis = {
            "string_resources": string_resources,
            "reveal_passwords": reveal_passwords,
            "changeable_icons": changeable_icons,
        }
        app.set_possible_modifications_analysis(possible_modifications_analysis=possible_modifications_analysis)


    def _analyze_single_apk(self, apk_path, source_information, string_resources=[], reveal_passwords=[],
                            changeable_icons=[]):
        tmp_dir = fs_utils.get_tmp_dir(self.tmp_dir, "tika-unpack")
        os.makedirs(tmp_dir)
        tool_unpack = ToolApkToolUnpack(tool_path=self.apktool_path, input_file=apk_path, output_dir=tmp_dir,
                                        decode_smali=False, decode_smali_only_main_classes=False,
                                        decode_resources=True,
                                        decode_resources_only_manifest=False,
                                        decode_assets=False)
        result = tool_unpack.execute()
        if result["success"]:
            self.check_modifications(tmp_dir, source_information, string_resources, reveal_passwords, changeable_icons)
        fs_utils.destroy_dir_files(tmp_dir)

    def check_modifications(self, unpacked_dir, source_information, string_resources=[], reveal_passwords=[],
                            changeable_icons=[]):
        tool_change_strings = ToolChangeStringResource(input_dir=unpacked_dir, skip_modifications=True)
        tool_change_strings_result = tool_change_strings.execute()
        if tool_change_strings_result["success"]:
            for file_change in tool_change_strings.file_changes:
                string_resources.append({
                    "source": source_information,
                    "resource_key": tool_change_strings.key_to_change,
                    "file": file_change["xml_path"],
                    "old_value": file_change["old_value"],
                    "new_value": file_change["new_value"],
                })

        tool_reveal_passwords = ToolRevealPasswordFields(input_dir=unpacked_dir, skip_modifications=True)
        tool_reveal_passwords_result = tool_reveal_passwords.execute()
        if tool_reveal_passwords_result["success"]:
            for file in tool_reveal_passwords.files_changed:
                reveal_passwords.append({
                    "source": source_information,
                    "file": file})

        tool_change_icons = ToolChangeIconResource(input_dir=unpacked_dir, skip_modifications=True)
        tool_change_icons_result = tool_change_icons.execute()
        if tool_change_icons_result["success"]:
            for file in tool_change_icons.edited_files:
                changeable_icons.append({
                    "source": source_information,
                    "file": file
                })

    def save_analysis(self, app: App):
        self.register_log(
            "possible_string_resources_modifications",
            ["source", "resource_key", "file", "old_value", "new_value"]
        )
        self.register_log(
            "possible_images_modifications",
            ["source", "file"]
        )
        self.register_log(
            "possible_layout_modifications",
            ["source", "file"]
        )
        possible_modifications_analysis = app.get_possible_modifications_analysis()
        if possible_modifications_analysis is not None:
            string_resources = possible_modifications_analysis.get("string_resources", [])
            reveal_passwords = possible_modifications_analysis.get("reveal_passwords", [])
            changeable_icons = possible_modifications_analysis.get("changeable_icons", [])
            for item in string_resources:
                self.record_log("possible_string_resources_modifications",
                                app,
                                [item["source"], item["resource_key"], item["file"], item["old_value"], item["new_value"]])
            for item in reveal_passwords:
                self.record_log("possible_images_modifications",
                                app,
                                [item["source"], item["file"]])
            for item in changeable_icons:
                self.record_log("possible_layout_modifications",
                                app,
                                [item["source"], item["file"]])
