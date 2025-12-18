import shutil
import logging
import os
from pymate.instrumate.instrumate_log import InstruMateLog
from pymate.common.app import App
from pymate.common.app_variant import AppVariant
from pymate.common import app_variant as av
from pymate.common.tool import BaseTool
from pymate.utils import fs_utils, utils
from abc import abstractmethod
from pathlib import Path



class MakerContext:
    def __init__(self, input_app: App, spec: AppVariant):
        self.input_app = input_app
        self.output_app = None
        self.spec = spec
        self.merged_apk = None
        self.context_data = {}


class VariantMaker:
    def __init__(self, name: str = None, tag: str = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        if name is not None:
            self.name = name
        else:
            self.name = self.__class__.__name__
        if tag is not None:
            self.tag = tag
        else:
            self.tag = self.__class__.__name__
        self.tmp_dir = None
        self.output_dir = None
        self.tools_dir = None
        self.instrumate_log = None
        self.force_overwrite = None
        self.append_to_existing = None
        self.tool_zipalign = None
        self.tool_apksigner = None
        self.apk_signer_key = None
        self.apk_signer_cert = None
        self.apktool_path = None
        self.dex2jar_path = None
        self.apkeditor_tool_path = None
        self.tool_droidfax = None
        self.tool_acvtool = None
        self.tool_aapt2 = None
        self.tool_adb = None
        self.tool_apksigner_bat = None
        self.tool_acvpatcher = None
        self.tool_aspectj_home = None
        self.tool_rv_android = None
        self.tool_aspectj_coverage = None
        self.tool_d8_path = None
        self.tool_cosmo = None
        self.tool_androlog = None
        self.jdk8_path = None
        self.jdk17_path = None
        self.android_sdk_libs = None
        self.tool_frida_gadgets = None

    def configure(self, tmp_dir: str = None, output_dir: str = None, tools_dir: str = None,
                  instrumate_log: InstruMateLog = None, force_overwrite=False,
                  append_to_existing=False,
                  jdk8_path=None, jdk17_path=None):
        self.tmp_dir = tmp_dir
        self.output_dir = output_dir
        self.tools_dir = tools_dir
        self.instrumate_log = instrumate_log
        self.force_overwrite = force_overwrite
        self.append_to_existing = append_to_existing
        if utils.is_windows():
            self.tool_zipalign = os.path.join(self.tools_dir, 'misc', 'zipalign.exe')
            self.tool_aapt2 = os.path.join(self.tools_dir, 'misc', 'aapt2.exe')
            self.tool_adb = os.path.join(self.tools_dir, 'platform-tools', 'adb.exe')
            self.tool_acvpatcher = os.path.join(self.tools_dir, 'acvpatcher', 'ACVPatcher-windows', 'ACVPatcher.exe')
            self.tool_apksigner_bat = os.path.join(self.tools_dir, 'misc', 'apksigner.bat')
        else:
            self.tool_zipalign = shutil.which('zipalign')
            self.tool_aapt2 = str(Path(os.path.join(self.tools_dir, 'misc', 'aapt2')).resolve())
            self.tool_adb = shutil.which('adb')
            self.tool_acvpatcher = str(Path(os.path.join(self.tools_dir, 'acvpatcher', 'ACVPatcher-linux', 'ACVPatcher')).resolve())
            self.tool_apksigner_bat = shutil.which('apksigner')
        self.tool_apksigner = os.path.join(self.tools_dir, 'misc', 'apksigner.jar')
        self.apk_signer_key = os.path.join(self.tools_dir, 'misc', 'signkey.pk8')
        self.apk_signer_cert = os.path.join(self.tools_dir, 'misc', 'signkey.x509.pem')
        self.apktool_path = os.path.join(self.tools_dir, 'misc', "apktool.jar")
        self.dex2jar_path = os.path.join(self.tools_dir, 'misc', 'dex-tools')
        self.apkeditor_tool_path = os.path.join(self.tools_dir, 'misc', 'APKEditor.jar')
        self.tool_d8_path = os.path.join(self.tools_dir, "misc", "d8.jar")
        self.tool_droidfax = os.path.join(self.tools_dir, "droidfax")
        self.tool_acvtool = os.path.join(self.tools_dir, "acvtool")
        self.tool_aspectj_home = os.path.join(self.tools_dir, 'aspectj1.9')
        self.tool_rv_android = os.path.join(self.tools_dir, 'rv-android')
        self.android_sdk_libs = os.path.join(self.tools_dir, 'android-sdk')
        self.tool_aspectj_coverage = os.path.join(self.tools_dir, 'aspectj-coverage')
        self.tool_cosmo = os.path.join(self.tools_dir, 'cosmo')
        self.tool_androlog = os.path.join(self.tools_dir, 'androlog', 'androlog.jar')
        self.tool_frida_gadgets = os.path.join(self.tools_dir, 'frida-gadget')
        self.jdk8_path = jdk8_path
        self.jdk17_path = jdk17_path
        if not os.path.exists(self.apktool_path):
            raise RuntimeError(f'File does not exists {self.apktool_path}')
        if not os.path.exists(self.dex2jar_path):
            raise RuntimeError(f'File does not exists {self.dex2jar_path}')
        if not os.path.exists(self.apkeditor_tool_path):
            raise RuntimeError(f'File does not exists {self.apkeditor_tool_path}')

    def get_final_variant_file(self, original_path, variant: AppVariant):
        extension = fs_utils.get_file_extension(original_path)
        original_file_name = fs_utils.get_file_name_without_extension(original_path)
        tag_str = self.tag
        variant_file_name = os.path.join(self.tmp_dir,
                                         f"{original_file_name}-F{variant.get_bin_features()}-L{variant.get_bin_levels()}-{tag_str}{extension}")
        return variant_file_name

    def get_target_sdk_jar(self, app: App):
        sdk_version = app.get_target_sdk_version()
        target_sdk = os.path.join(self.android_sdk_libs, f"android-{sdk_version}", "android.jar")
        if not os.path.exists(target_sdk):
            return None
        return target_sdk

    def get_tmp_file(self, extension=None, label=""):
        return fs_utils.get_tmp_file(tmp_dir=self.tmp_dir, tag=self.tag, label=label, extension=extension)

    def get_tmp_dir(self, label=""):
        return fs_utils.get_tmp_dir(tmp_dir=self.tmp_dir, tag=self.tag, label=label)

    def execute_tool(self, tool: BaseTool, context: MakerContext, fail_on_error=True):
        variant = context.spec
        result = tool.execute()
        variant_maker = self.name
        variant_maker_tag = self.tag
        tool_name = result["name"] if "name" in result else None
        tool_description = result["description"] if "description" in result else None
        tool_success = result["success"] if "success" in result else None
        tool_cmd_stdout = result["cmd_stdout"] if "cmd_stdout" in result else None
        tool_cmd_stderr = result["cmd_stderr"] if "cmd_stderr" in result else None
        tool_script_stdout = result["script_stdout"] if "script_stdout" in result else None
        tool_script_stderr = result["script_stderr"] if "script_stderr" in result else None
        tool_traceback_exception = result["tb_exception"] if "tb_exception" in result else None
        tool_total_secs = result["total_secs"] if "total_secs" in result else None
        tool_options_dict = result["options"] if "options" in result else {}
        tool_options_dict["fail_on_error"] = fail_on_error
        tool_options = utils.dict_as_formatted_json(tool_options_dict)
        self.instrumate_log.log_variant_maker_tool_exec(variant_maker, variant_maker_tag, tool_name, tool_description,
                                                        context.input_app.get_base_pkg(),
                                                        context.input_app.get_package_name(),
                                                        context.input_app.get_app_version_name(),
                                                        context.input_app.get_app_id(),
                                                        variant.get_bin_features(), variant.get_feature_labels(),
                                                        variant.get_bin_levels(), variant.get_level_labels(),
                                                        tool_success, tool_cmd_stdout, tool_cmd_stderr,
                                                        tool_script_stdout,
                                                        tool_script_stderr,
                                                        tool_traceback_exception,
                                                        tool_total_secs,
                                                        tool_options)
        if not tool_success and fail_on_error:
            raise RuntimeError(f"EXECUTE TOOL FAILED: {tool_name} {tool_cmd_stdout} {tool_cmd_stderr}")
        return result

    def can_make(self, app: App, variant: AppVariant):
        if not variant.is_at_least_one_feature_active(self.get_known_features()):
            self.logger.debug(f"Rejected for not knowing any feature - {self.tag} - {variant.get_feature_labels()}")
            return False
        if variant.is_other_feature_active(self.get_known_features()):
            other_features = [av.FEATURE_LABELS[key] for key in av.FEATURE_LABELS if
                              key not in self.get_known_features() and variant.is_feature_set(key)]
            self.logger.debug(
                f"Rejected for not knowing specific features - {self.tag}. Features: {str(other_features)}")
            return False
        if variant.is_feature_set(av.FEATURE_MERGED_APP) and not app.has_split_pkgs():
            self.logger.debug(f"Rejected because it is not possible to merge if it has no splits.")
            return False
        return True

    def pre_process(self, context: MakerContext):
        pass

    def merge(self, context: MakerContext):
        raise NotImplementedError("Subclasses should implement this method")

    @abstractmethod
    def unpack(self, context: MakerContext):
        raise NotImplementedError('This method should be implemented by subclasses')

    @abstractmethod
    def modify(self, context: MakerContext):
        raise NotImplementedError('This method should be implemented by subclasses')

    @abstractmethod
    def repack(self, context: MakerContext):
        raise NotImplementedError('This method should be implemented by subclasses')

    def post_process(self, context: MakerContext):
        pass

    @abstractmethod
    def get_known_features(self):
        raise NotImplementedError('This method should be implemented by subclasses')

    def make_variant(self, input_app: App, input_spec: AppVariant) -> (App, AppVariant):
        context = MakerContext(input_app=input_app, spec=input_spec)
        self.pre_process(context)
        if context.spec.is_feature_set(av.FEATURE_MERGED_APP):
            self.merge(context)
        self.unpack(context)
        self.modify(context)
        self.repack(context)
        self.post_process(context)
        if context.output_app is None:
            raise RuntimeError(f"output app shouldn't be none {self.name}")
        return context.output_app
