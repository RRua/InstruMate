import os
from pymate.common import app_variant as av
from pymate.common.app import App, AppVariant
from pymate.instrumate.variant_maker import MakerContext
from pymate.instrumate.variant_makers.Deprecateds.DeprecatedRepackagerByApkEditor import RepackagerByApkEditor
from pymate.utils import fs_utils
from pymate.common.tools.ToolZip import ToolZipUnpack, ToolZipRepack
from pymate.common.tools.ToolCosmoInstrumentation import ToolCosmoInstrumentation
from pymate.common.tools.ToolManifestEditor import ToolManifestEditor

class RepackagerByCOSMO(RepackagerByApkEditor):

    def __init__(self, name=None, tag='by-COSMO'):
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
            av.FEATURE_MONITOR_METHOD_CALLS_WITH_COSMO,
            av.FEATURE_MERGED_APP
        ]

    def can_make(self, app: App, variant: AppVariant):
        knows_features = super().can_make(app, variant)
        if not knows_features:
            return False
        if not variant.is_feature_set(av.FEATURE_MONITOR_METHOD_CALLS_WITH_COSMO):
            return False
        else:
            if not variant.is_level_set(av.VARIANT_LEVEL_MODIFY_RESOURCES):
                return False
        if variant.is_feature_set(av.FEATURE_MERGED_APP) and not app.has_split_pkgs():
            return False
        return True

    def modify_single_apk(self, unpacked_dir, is_base: bool, context: MakerContext):
        self._modify_manifest(unpacked_dir=unpacked_dir, is_base=is_base, context=context)
        variant = context.spec
        cosmo_jars = [item for item in fs_utils.list_files(os.path.join(self.tool_cosmo, 'lib')) if
                        "jacocoagent" in item or "receiver" in item]
        if variant.is_feature_set(av.FEATURE_MONITOR_METHOD_CALLS_WITH_COSMO):
            if "dex_2_jar" in context.context_data:
                dex_2_jar = context.context_data["dex_2_jar"]
                if unpacked_dir in dex_2_jar:
                    jar_file = dex_2_jar[unpacked_dir]
                    instrumented_dir = self.get_tmp_dir()
                    if not os.path.exists(instrumented_dir):
                        os.makedirs(instrumented_dir)
                    self.execute_tool(
                        ToolCosmoInstrumentation(cosmo_dir=self.tool_cosmo, jdk8_path=self.jdk8_path, input_file=jar_file, output_dir=instrumented_dir))
                    for file in fs_utils.list_files(instrumented_dir):
                        self.execute_tool(ToolZipUnpack(input_file=file, output_dir=instrumented_dir,
                                                        fail_on_ms_windows_overwrite=False,
                                                        merge_with_existing_outputdir=True))
                        os.remove(file)
                    for file in cosmo_jars:
                        self.execute_tool(ToolZipUnpack(input_file=file, output_dir=instrumented_dir,
                                                        fail_on_ms_windows_overwrite=False,
                                                        merge_with_existing_outputdir=True))
                    fs_utils.destroy_dir_files(os.path.join(instrumented_dir, "META-INF"))
                    os.remove(os.path.join(instrumented_dir, 'about.html'))
                    instrumented_jar = self.get_tmp_file(extension="jar")
                    self.execute_tool(ToolZipRepack(input_dir=instrumented_dir, output_file=instrumented_jar))
                    fs_utils.destroy_dir_files(instrumented_dir)
                    dex_2_jar[unpacked_dir] = instrumented_jar
                    # context.context_data["jar_2_dex"][key] = result_dir

    def _modify_manifest(self, unpacked_dir, is_base: bool, context: MakerContext):
        variant = context.spec
        debuggable = variant.is_feature_set(av.FEATURE_DEBUGGABLE)
        trust_user_installed_certs = variant.is_feature_set(av.FEATURE_TRUST_USER_INSTALLED_CERTS)
        allow_data_backup = variant.is_feature_set(av.FEATURE_ALLOW_PRIVATE_DATA_BKP)
        add_cosmo_broadcast_receiver = variant.is_feature_set(av.FEATURE_MONITOR_METHOD_CALLS_WITH_COSMO)
        if debuggable or trust_user_installed_certs or allow_data_backup or add_cosmo_broadcast_receiver:
            manifest_file = os.path.join(unpacked_dir, "AndroidManifest.xml")
            if os.path.exists(manifest_file):
                self.execute_tool(ToolManifestEditor(input_file=manifest_file, allows_private_backups=allow_data_backup,
                                                     flag_add_debuggable=debuggable,
                                                     add_cosmo_broadcast_receiver=add_cosmo_broadcast_receiver,
                                                     accept_user_installed_ca_certs=trust_user_installed_certs))