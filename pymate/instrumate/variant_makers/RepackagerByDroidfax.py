from pymate.instrumate.variant_makers.GenericApkToolRepackager import GenericApkToolRepackager
from pymate.common import app_variant as av
from pymate.instrumate.variant_maker import MakerContext
from pymate.utils import fs_utils
from pymate.common.tools.ToolDroidfaxInstrumentation import ToolDroidfaxInstrumentation, MODE_DYNAMIC_CALL_GRAPH


class RepackagerByDroidfax(GenericApkToolRepackager):

    def __init__(self, tag='by-droidfax'):
        super().__init__(tag=tag)

    def get_known_features(self):
        return [av.FEATURE_MONITOR_METHOD_CALLS_WITH_DROIDFAX]

    def unpack_single_apk(self, file_path, is_base: bool, context: MakerContext) -> str:
        return None

    def convert_to_instrumentation_representation(self, apk_file, unpacked_dir, is_base, context: MakerContext) -> str:
        return None

    def instrument(self, apk_file: str, unpacked_dir: str, instrumentable_version: str, is_base,
                   context: MakerContext) -> str:
        return None

    def modify_single_apk(self, apk_file: str, unpacked_dir: str, is_base: bool, context: MakerContext):
        pass

    def repack_single_apk(self, apk_file, unpacked_dir: str, instrumentable_version: str, instrumented_version: str,
                          is_base: bool, context: MakerContext):
        output_dir = self.get_tmp_dir(label="repack")
        self.execute_tool(
            ToolDroidfaxInstrumentation(droidfax_dir=self.tool_droidfax, input_file=apk_file,
                                        output_dir=output_dir, mode=MODE_DYNAMIC_CALL_GRAPH,
                                        jdk8_path=self.jdk8_path), context)
        created_app = fs_utils.list_files(output_dir)
        assert len(created_app) == 1
        return created_app.pop()
