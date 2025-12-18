import os
from pymate.instrumate.variant_makers.GenericApkEditorRepackager import GenericApkEditorRepackager
from pymate.common import app_variant as av
from pymate.instrumate.variant_maker import MakerContext
from pymate.instrumate.instrumate_log import InstruMateLog
from pymate.utils import fs_utils
from pymate.common.tools.ToolFridaSmaliPatcher import ToolFridaSmaliPatcher


def list_classes_subdirectories(directory: str):
    smali_dirs = []
    for entry in os.scandir(directory):
        if entry.is_dir() and 'classes' in entry.name:
            smali_dirs.append(entry.path)
    return smali_dirs


class RepackagerByFridaGadgetWithApkEditor(GenericApkEditorRepackager):

    def __init__(self, tag='by-fridagadgetapkeditor'):
        super().__init__(tag=tag)
        self.architectures = []
        self.gadget_new_name = "instrumate"
        self.maximize_injections = True
        self.gadget_map = {}
        self.architectures = ['arm', 'arm64', 'x86', 'x86_64']
        self.script_file = None

    def configure(self, tmp_dir: str = None, output_dir: str = None, tools_dir: str = None,
                  instrumate_log: InstruMateLog = None, force_overwrite=False,
                  append_to_existing=False,
                  jdk8_path=None, jdk17_path=None):
        super().configure(tmp_dir, output_dir, tools_dir,
                          instrumate_log, force_overwrite,
                          append_to_existing,
                          jdk8_path, jdk17_path)

        arch_dirnames = {'arm': 'armeabi-v7a',
                         'x86': 'x86',
                         'arm64': 'arm64-v8a',
                         'x86_64': 'x86_64'}
        shared_objects = fs_utils.list_files(self.tool_frida_gadgets, extension="so")

        for key in arch_dirnames:
            arch_dir = arch_dirnames[key]
            for shared_obj in shared_objects:
                search_str = f"-{key}.so"
                if search_str in shared_obj:
                    self.gadget_map[arch_dir] = shared_obj
                    break
        self.script_file = [file for file in fs_utils.list_files(self.tool_frida_gadgets, extension="js") if
                            "disabled" not in file][0]

    def get_known_features(self):
        return [av.FEATURE_MONITOR_METHOD_CALLS_WITH_FRIDA_GADGET, av.FEATURE_MERGED_APP]

    def convert_to_instrumentation_representation(self, apk_file, unpacked_dir, is_base, context: MakerContext) -> str:
        smali_dir = os.path.join(unpacked_dir, "smali")
        if os.path.exists(smali_dir):
            smali_dirs = list_classes_subdirectories(smali_dir)
            if len(smali_dirs) > 0:
                return smali_dirs
        if is_base:
            raise RuntimeError("Cant inject frida. No Smali folder.")
        return None

    def instrument(self, apk_file: str, unpacked_dir: str, instrumentable_version: str, is_base,
                   context: MakerContext) -> str:
        smali_dirs = instrumentable_version
        qtd_injections = 0
        for smali_dir in smali_dirs:
            main_activity = context.input_app.get_main_activity()
            activities = context.input_app.get_activities()
            injectable_activities = [main_activity] + activities
            lib_dir = os.path.join(unpacked_dir, 'root', 'lib')
            if not os.path.exists(lib_dir):
                os.makedirs(lib_dir)
            tool_frida_patcher = ToolFridaSmaliPatcher(smali_dir=smali_dir,
                                  lib_dir=lib_dir,
                                  js_file_path=self.script_file,
                                  new_library_name=self.gadget_new_name,
                                  target_smali_files=injectable_activities,
                                  maximize_injection=True,
                                  archs=self.gadget_map,
                                  upload_lib=is_base)
            self.execute_tool(tool_frida_patcher, context)
            qtd_injections = qtd_injections + tool_frida_patcher.qtd_injections
        if is_base and qtd_injections == 0:
            raise RuntimeError("Injection failed")
        self.logger.debug(f"Successfully injected frida gadget")
        return instrumentable_version
