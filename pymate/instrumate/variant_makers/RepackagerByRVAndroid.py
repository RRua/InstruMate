import os
from pymate.instrumate.variant_makers.GenericApkToolRepackager import GenericApkToolRepackager
from pymate.common import app_variant as av
from pymate.instrumate.variant_maker import MakerContext
from pymate.utils import fs_utils
from pymate.common.tools.ToolZip import ToolZipUnpack, ToolZipRepack
from pymate.common.tools.ToolAspectjInstrumentation import ToolAspectjInstrumentation


class RepackagerByRVAndroid(GenericApkToolRepackager):

    def __init__(self, tag='by-rvandroid'):
        super().__init__(tag=tag)

    def get_known_features(self):
        return [av.FEATURE_MONITOR_CRYPTO_API_MISUSE]

    def unpack_single_apk(self, file_path, is_base: bool, context: MakerContext) -> str:
        return super().unpack_single_apk(file_path, is_base, context)

    def convert_to_instrumentation_representation(self, apk_file, unpacked_dir, is_base, context: MakerContext) -> str:
        return self.convert_to_java_instrumentation_representation(apk_file, unpacked_dir, is_base, context)

    def instrument(self, apk_file: str, unpacked_dir: str, instrumentable_version: str, is_base,
                   context: MakerContext) -> str:
        target_sdk_jar = self.get_target_sdk_jar(app=context.input_app)
        aspectj_jars = fs_utils.list_files(os.path.join(self.tool_aspectj_home, 'lib'))
        rv_android_jars = fs_utils.list_files(os.path.join(self.tool_rv_android, 'lib'))
        rv_android_aspects_dir = os.path.join(self.tool_rv_android, 'aspects')
        tmp_dir_for_libs = self.get_tmp_dir(label="libs_dir")
        if not os.path.exists(tmp_dir_for_libs):
            os.makedirs(tmp_dir_for_libs)
        for file in list(aspectj_jars) + list(rv_android_jars) + [target_sdk_jar]:
            fs_utils.copy_file(file, tmp_dir_for_libs)
        jar_file = instrumentable_version
        jar_file_unpacked = self.get_tmp_dir(label="jar_unpacked")
        self.execute_tool(ToolZipUnpack(input_file=jar_file, output_dir=jar_file_unpacked,
                                        fail_on_ms_windows_overwrite=True), context)
        woven_dir = self.get_tmp_dir(label="woven")
        if not os.path.exists(woven_dir):
            os.makedirs(woven_dir)
        self.execute_tool(
            ToolAspectjInstrumentation(jdk17_home_dir=self.jdk17_path, libs_dir=tmp_dir_for_libs,
                                       dir_to_be_woven=jar_file_unpacked,
                                       root_dir_for_src_files=rv_android_aspects_dir, output_dir=woven_dir), context)
        fs_utils.destroy_dir_files(jar_file_unpacked)
        for file in fs_utils.list_files(tmp_dir_for_libs):
            if "aspectjrt" in file or "rv-monitor-rt" in file or "rvsec-core" in file or "rvsec-logger-logcat" in file:
                self.execute_tool(ToolZipUnpack(input_file=file, output_dir=woven_dir,
                                                fail_on_ms_windows_overwrite=False,
                                                merge_with_existing_outputdir=True), context)
        fs_utils.destroy_dir_files(os.path.join(woven_dir, "META-INF"))
        woven_jar = self.get_tmp_file(extension="jar")
        self.execute_tool(ToolZipRepack(input_dir=woven_dir, output_file=woven_jar), context)
        fs_utils.destroy_dir_files(woven_dir)
        fs_utils.destroy_dir_files(tmp_dir_for_libs)
        return woven_jar

    def modify_single_apk(self, apk_file: str, unpacked_dir: str, is_base: bool, context: MakerContext):
        pass

    def repack_single_apk(self, apk_file, unpacked_dir: str, instrumentable_version: str, instrumented_version: str,
                          is_base: bool, context: MakerContext):
        super().convert_instrumented_java_to_dex(apk_file=apk_file, unpacked_dir=unpacked_dir,
                                                 instrumented_version=instrumented_version, is_base=is_base,
                                                 context=context)
        return super().repack_single_apk(apk_file, unpacked_dir, instrumentable_version, instrumented_version, is_base,
                                         context)
