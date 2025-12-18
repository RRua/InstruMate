import os
from pymate.common.app import App
from pymate.common.app_variant import AppVariant
from pymate.instrumate.variant_makers.GenericApkToolRepackager import GenericApkToolRepackager
from pymate.common import app_variant as av
from pymate.instrumate.variant_maker import MakerContext
from pymate.utils import fs_utils
from pymate.common.tools.ToolZip import ToolZipUnpack, ToolZipRepack
from pymate.common.tools.ToolManifestEditor import ToolManifestEditor
from pymate.common.tools.ToolCosmoInstrumentation import ToolCosmoInstrumentation


class RepackagerByCOSMO(GenericApkToolRepackager):

    def __init__(self, tag='by-cosmo'):
        super().__init__(tag=tag)

    def get_known_features(self):
        return [av.FEATURE_MONITOR_METHOD_CALLS_WITH_COSMO]

    def can_make(self, app: App, variant: AppVariant):
        knows_features = super().can_make(app, variant)
        if not knows_features:
            return False
        if not variant.is_level_set(av.VARIANT_LEVEL_MODIFY_MANIFEST):
            return False
        return True

    def unpack_single_apk(self, file_path, is_base: bool, context: MakerContext) -> str:
        return super().unpack_single_apk(file_path, is_base, context)

    def convert_to_instrumentation_representation(self, apk_file, unpacked_dir, is_base, context: MakerContext) -> str:
        return self.convert_to_java_instrumentation_representation(apk_file, unpacked_dir, is_base, context)

    def instrument(self, apk_file: str, unpacked_dir: str, instrumentable_version: str, is_base,
                   context: MakerContext) -> str:
        cosmo_jars = [item for item in fs_utils.list_files(os.path.join(self.tool_cosmo, 'lib')) if
                      "jacocoagent" in item or "receiver" in item]
        jar_file = instrumentable_version
        instrumented_dir = self.get_tmp_dir(label="instrument")
        if not os.path.exists(instrumented_dir):
            os.makedirs(instrumented_dir)
        self.execute_tool(
            ToolCosmoInstrumentation(cosmo_dir=self.tool_cosmo, jdk8_path=self.jdk8_path,
                                     input_file=jar_file, output_dir=instrumented_dir), context)
        for file in fs_utils.list_files(instrumented_dir):
            self.execute_tool(ToolZipUnpack(input_file=file, output_dir=instrumented_dir,
                                            fail_on_ms_windows_overwrite=False,
                                            merge_with_existing_outputdir=True), context)
            os.remove(file)
        for file in cosmo_jars:
            self.execute_tool(ToolZipUnpack(input_file=file, output_dir=instrumented_dir,
                                            fail_on_ms_windows_overwrite=False,
                                            merge_with_existing_outputdir=True), context)
        fs_utils.destroy_dir_files(os.path.join(instrumented_dir, "META-INF"))
        os.remove(os.path.join(instrumented_dir, 'about.html'))
        instrumented_jar = self.get_tmp_file(extension="jar")
        self.execute_tool(ToolZipRepack(input_dir=instrumented_dir, output_file=instrumented_jar), context)
        fs_utils.destroy_dir_files(instrumented_dir)
        return instrumented_jar

    def modify_single_apk(self, apk_file: str, unpacked_dir: str, is_base: bool, context: MakerContext):
        variant = context.spec
        add_cosmo_broadcast_receiver = variant.is_feature_set(av.FEATURE_MONITOR_METHOD_CALLS_WITH_COSMO)
        if add_cosmo_broadcast_receiver:
            manifest_file = os.path.join(unpacked_dir, "AndroidManifest.xml")
            if os.path.exists(manifest_file):
                self.execute_tool(ToolManifestEditor(input_file=manifest_file, allows_private_backups=False,
                                                     flag_add_debuggable=False,
                                                     add_cosmo_broadcast_receiver=add_cosmo_broadcast_receiver,
                                                     accept_user_installed_ca_certs=False), context)
            else:
                raise RuntimeError("No manifest to be configured to use cosmo")

    def repack_single_apk(self, apk_file, unpacked_dir: str, instrumentable_version: str, instrumented_version: str,
                          is_base: bool, context: MakerContext):
        super().convert_instrumented_java_to_dex(apk_file=apk_file, unpacked_dir=unpacked_dir,
                                                 instrumented_version=instrumented_version, is_base=is_base,
                                                 context=context)
        return super().repack_single_apk(apk_file, unpacked_dir, instrumentable_version, instrumented_version, is_base,
                                         context)
