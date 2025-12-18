import os
from pymate.common import app_variant as av
from pymate.common.app import App, AppVariant
from pymate.instrumate.variant_maker import MakerContext
from pymate.instrumate.variant_makers.Deprecateds.DeprecatedRepackagerByApkEditor import RepackagerByApkEditor
from pymate.utils import fs_utils
from pymate.common.tools.ToolZip import ToolZipUnpack, ToolZipRepack
from pymate.common.tools.ToolAspectjInstrumentation import ToolAspectjInstrumentation


class RepackagerByRVAndroid(RepackagerByApkEditor):

    def __init__(self, name=None, tag='by-rvandroid'):
        if name is None:
            super().__init__(name=self.__class__.__name__, tag=tag)
        else:
            super().__init__(name=name, tag=tag)

    def get_known_features(self):
        return [
            av.FEATURE_REPACKAGED,
            # av.FEATURE_DEBUGGABLE,
            # av.FEATURE_ALLOW_PRIVATE_DATA_BKP,
            # av.FEATURE_TRUST_USER_INSTALLED_CERTS,
            # av.FEATURE_REVEAL_PASSWORD_FIELDS,
            # av.FEATURE_MONITOR_SENSITIVE_APIS_SMALI,
            # av.FEATURE_MONITOR_SENSITIVE_APIS_JAVA_AOP,
            av.FEATURE_MONITOR_CRYPTO_API_MISUSE,
            av.FEATURE_MERGED_APP
        ]

    def can_make(self, app: App, variant: AppVariant):
        knows_features = super().can_make(app, variant)
        if not knows_features:
            return False
        if not variant.is_feature_set(av.FEATURE_MONITOR_CRYPTO_API_MISUSE):
            return False
        if variant.is_feature_set(av.FEATURE_MERGED_APP) and not app.has_split_pkgs():
            return False
        return True

    def modify_single_apk(self, unpacked_dir, is_base: bool, context: MakerContext):
        super().modify_single_apk(unpacked_dir=unpacked_dir, is_base=is_base, context=context)
        variant = context.spec
        target_sdk_jar = self.get_target_sdk_jar(app=context.input_app)
        aspectj_jars = fs_utils.list_files(os.path.join(self.tool_aspectj_home, 'lib'))
        rv_android_jars = fs_utils.list_files(os.path.join(self.tool_rv_android, 'lib'))
        rv_android_aspects_dir = os.path.join(self.tool_rv_android, 'aspects')
        tmp_dir_for_libs = self.get_tmp_dir()
        if not os.path.exists(tmp_dir_for_libs):
            os.makedirs(tmp_dir_for_libs)
        for file in list(aspectj_jars) + list(rv_android_jars) + [target_sdk_jar]:
            fs_utils.copy_file(file, tmp_dir_for_libs)
        if variant.is_feature_set(av.FEATURE_MONITOR_CRYPTO_API_MISUSE):
            if "dex_2_jar" in context.context_data:
                dex_2_jar = context.context_data["dex_2_jar"]
                if unpacked_dir in dex_2_jar:
                    jar_file = dex_2_jar[unpacked_dir]
                    jar_file_unpacked = self.get_tmp_dir()
                    self.execute_tool(ToolZipUnpack(input_file=jar_file, output_dir=jar_file_unpacked,
                                                    fail_on_ms_windows_overwrite=True))
                    woven_dir = self.get_tmp_dir()
                    if not os.path.exists(woven_dir):
                        os.makedirs(woven_dir)
                    self.execute_tool(
                        ToolAspectjInstrumentation(jdk17_home_dir=self.jdk17_path, libs_dir=tmp_dir_for_libs,
                                                   dir_to_be_woven=jar_file_unpacked,
                                                   root_dir_for_src_files=rv_android_aspects_dir, output_dir=woven_dir))
                    fs_utils.destroy_dir_files(jar_file_unpacked)
                    for file in fs_utils.list_files(tmp_dir_for_libs):
                        if "aspectjrt" in file or "rv-monitor-rt" in file or "rvsec-core" in file or "rvsec-logger-logcat" in file:
                            self.execute_tool(ToolZipUnpack(input_file=file, output_dir=woven_dir,
                                                            fail_on_ms_windows_overwrite=False,
                                                            merge_with_existing_outputdir=True))
                    fs_utils.destroy_dir_files(os.path.join(woven_dir, "META-INF"))
                    woven_jar = self.get_tmp_file(extension="jar")
                    self.execute_tool(ToolZipRepack(input_dir=woven_dir, output_file=woven_jar))
                    fs_utils.destroy_dir_files(woven_dir)
                    dex_2_jar[unpacked_dir] = woven_jar
                    # context.context_data["jar_2_dex"][key] = result_dir
        fs_utils.destroy_dir_files(tmp_dir_for_libs)
