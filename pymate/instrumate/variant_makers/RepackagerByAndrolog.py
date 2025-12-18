import os
from pymate.instrumate.variant_makers.GenericApkToolRepackager import GenericApkToolRepackager
from pymate.common import app_variant as av
from pymate.instrumate.variant_maker import MakerContext
from pymate.utils import fs_utils
from pymate.common.tools.ToolAndrologInstrumentation import ToolAndrologInstrumentation
from pymate.common.tools.ToolZip import ToolZipUnpack, ToolZipRepack
from pymate.instrumate.variant_makers.GenericZipRepackager import remove_signature_files

class RepackagerByAndrolog(GenericApkToolRepackager):

    def __init__(self, tag='by-androlog'):
        super().__init__(tag=tag)

    def get_known_features(self):
        return [av.FEATURE_MONITOR_METHOD_CALLS_WITH_ANDROLOG, av.FEATURE_MERGED_APP]

    def unpack_single_apk(self, file_path, is_base: bool, context: MakerContext) -> str:
        return None

    def convert_to_instrumentation_representation(self, apk_file, unpacked_dir, is_base, context: MakerContext) -> str:
        return None

    def instrument(self, apk_file: str, unpacked_dir: str, instrumentable_version: str, is_base,
                   context: MakerContext) -> str:
        return None

    def modify_single_apk(self, apk_file: str, unpacked_dir: str, is_base: bool, context: MakerContext):
        pass

    def _unpack(self, apk_file, is_base, context):
        pass

    def _modify(self, apk_file: str, is_base: bool, context: MakerContext):
        pass

    def _remove_signature(self, apk_file, context):
        unpack_dir_path = self.get_tmp_dir(label="unpack")
        self.execute_tool(ToolZipUnpack(input_file=apk_file, output_dir=unpack_dir_path,
                                        fail_on_ms_windows_overwrite=True), context)
        meta_inf_dir = os.path.join(unpack_dir_path, "META-INF")
        if os.path.exists(meta_inf_dir):
            remove_signature_files(meta_inf_dir)
        tmp_file = self.get_tmp_file()
        self.execute_tool(ToolZipRepack(unpack_dir_path, tmp_file, not_compress_files=['resources.arsc', '.so']),
                          context)
        fs_utils.destroy_dir_files(unpack_dir_path)
        return tmp_file

    def repack_single_apk(self, apk_file, unpacked_dir: str, instrumentable_version: str, instrumented_version: str,
                          is_base: bool, context: MakerContext):
        app = context.input_app
        dex_files = app.get_dex_files_in_splits()
        contains_dex = False
        if is_base:
            contains_dex = True
        else:
            if fs_utils.zip_contains_files(apk_file, dex_files):
                contains_dex = True
        if not contains_dex:
            return self._remove_signature(apk_file, context)
        else:
            output_dir = self.get_tmp_dir(label="repack")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            target_sdk_jar = self.get_target_sdk_jar(app=context.input_app)
            if os.path.exists(target_sdk_jar):
                target_sdk_dir = fs_utils.get_immediate_parent_folder(fs_utils.get_immediate_parent_folder(target_sdk_jar))
            else:
                raise NotImplementedError("Specific jar for the expected sdk is missing")
            self.execute_tool(
                ToolAndrologInstrumentation(androlog_jar=self.tool_androlog, platform_dir=target_sdk_dir,
                                            input_file=apk_file,
                                            output_dir=output_dir), context)
            created_app = fs_utils.list_files(output_dir)
            assert len(created_app) == 1
            result_tmp = created_app.pop()
            final_result = self.get_tmp_file(extension="apk", label="repack")
            fs_utils.move_file(source=result_tmp, destination=final_result)
            fs_utils.destroy_dir_files(output_dir)
            return final_result
